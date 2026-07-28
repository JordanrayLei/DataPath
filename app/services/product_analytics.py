from __future__ import annotations

import hashlib
import math
import statistics
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import ProductEvent, QueryRun
from app.schemas.chatbi import ChatbiAskRequest, ChatbiAskResponse


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _candidate_observation(retrieval: dict[str, Any]) -> dict[str, Any]:
    candidates: dict[str, dict[str, Any]] = {}
    for mention in retrieval.get("mentions", []):
        for candidate in mention.get("candidates", []):
            metric_id = candidate.get("metric_id")
            if metric_id and (
                metric_id not in candidates
                or float(candidate.get("probability") or 0)
                > float(candidates[metric_id].get("probability") or 0)
            ):
                candidates[metric_id] = candidate
    ranked = sorted(
        candidates.values(),
        key=lambda item: (-float(item.get("probability") or 0), str(item.get("metric_id"))),
    )
    sources = sorted(
        {
            source
            for candidate in ranked
            for source in candidate.get("retrieval_sources", [])
        }
    )
    return {
        "candidate_count": len(ranked),
        "top1_metric_id": ranked[0].get("metric_id") if ranked else None,
        "top1_score": ranked[0].get("probability") if ranked else None,
        "top1_margin": round(
            float(ranked[0].get("probability") or 0)
            - (float(ranked[1].get("probability") or 0) if len(ranked) > 1 else 0),
            4,
        )
        if ranked
        else None,
        "retrieval_sources": sources,
        "embedding_used": "embedding" in sources,
        "reranker_used": "reranker" in sources,
    }


def _event(
    payload: ChatbiAskRequest,
    response: ChatbiAskResponse,
    event_name: str,
    *,
    status: str = "",
    reason_code: str = "",
    properties: dict[str, Any] | None = None,
    duration_ms: int | None = None,
) -> ProductEvent:
    operator = response.operator_id or "anonymous"
    traffic_class = (
        "test"
        if payload.conversation_id.startswith(("golden_", "test_"))
        else "interactive"
    )
    return ProductEvent(
        event_id=f"evt_{uuid.uuid4().hex[:24]}",
        workspace_id=payload.workspace_id,
        actor_hash=_hash(f"{payload.workspace_id}:{operator}"),
        conversation_hash=_hash(f"{payload.workspace_id}:{payload.conversation_id}"),
        trace_id=response.trace_id,
        query_id=(response.compiled or {}).get("query_id"),
        event_name=event_name,
        status=status,
        reason_code=reason_code,
        properties_json={"traffic_class": traffic_class, **(properties or {})},
        duration_ms=duration_ms,
    )


def record_ask_events(
    session: Session,
    payload: ChatbiAskRequest,
    response: ChatbiAskResponse,
    duration_ms: int,
) -> None:
    """Persist derived events without storing the question, SQL, or result rows."""

    retrieval = response.retrieval or {}
    reason_codes = retrieval.get("reason_codes") or []
    steps = {step.key: step for step in response.steps}
    inherited = "已继承上一轮" in (steps.get("context").detail if steps.get("context") else "")
    events = [
        _event(
            payload,
            response,
            "question_submitted",
            properties={
                "question_hash": _hash(payload.query.strip().casefold()),
                "question_length": len(payload.query),
                "biz_domain": response.biz_domain,
                "is_followup": inherited,
            },
        ),
        _event(
            payload,
            response,
            "status_decided",
            status=response.status,
            reason_code=str(reason_codes[0] if reason_codes else ""),
            properties={"pipeline_terminal_step": response.steps[-1].key if response.steps else ""},
            duration_ms=duration_ms,
        ),
    ]
    if retrieval:
        events.append(
            _event(
                payload,
                response,
                "retrieval_completed",
                status=str(retrieval.get("gate_status") or ""),
                reason_code=str(reason_codes[0] if reason_codes else ""),
                properties=_candidate_observation(retrieval),
            )
        )
        judge = (retrieval.get("runtime_diagnostics") or {}).get("metric_judge") or {}
        if judge.get("invoked"):
            decisions = judge.get("decisions") or []
            first = decisions[0] if decisions else {}
            events.append(
                _event(
                    payload,
                    response,
                    "metric_judge_completed",
                    status=str(first.get("decision") or retrieval.get("gate_status") or ""),
                    reason_code=str(first.get("reason_code") or ""),
                    properties={
                        "provider": judge.get("provider"),
                        "model": judge.get("model"),
                        "fallback": bool(judge.get("fallback")),
                        "confidence": first.get("confidence"),
                        "selected_metric_id": first.get("selected_metric_id"),
                        "candidate_count": sum(
                            len(item.get("candidates") or [])
                            for item in retrieval.get("mentions", [])
                        ),
                    },
                )
            )
    if response.execution:
        run = session.get(QueryRun, (response.compiled or {}).get("query_id"))
        events.append(
            _event(
                payload,
                response,
                "query_executed",
                status=str(response.execution.get("status") or ""),
                properties={
                    "metric_id": (response.selected_metric or {}).get("metric_id"),
                    "metric_version": (response.selected_metric or {}).get("metric_version"),
                    "row_count": response.execution.get("row_count"),
                    "execution_ms": response.execution.get("execution_ms"),
                    "estimated_rows": (run.estimated_cost or {}).get("estimated_rows") if run else None,
                },
                duration_ms=response.execution.get("execution_ms"),
            )
        )
    if response.interpretation or response.reflection:
        events.append(
            _event(
                payload,
                response,
                "answer_rendered",
                status=str((response.reflection or {}).get("status") or ""),
                properties={
                    "evidence_count": len((response.profile or {}).get("evidence") or []),
                    "chart_type": (response.interpretation or {}).get("chart_type"),
                },
            )
        )
    try:
        session.add_all(events)
        session.commit()
    except SQLAlchemyError:
        session.rollback()


def record_feedback_event(
    session: Session,
    *,
    workspace_id: str,
    conversation_id: str,
    operator_id: str,
    trace_id: str,
    query_id: str | None,
    feedback_type: str,
    severity: str,
) -> None:
    event = ProductEvent(
        event_id=f"evt_{uuid.uuid4().hex[:24]}",
        workspace_id=workspace_id,
        actor_hash=_hash(f"{workspace_id}:{operator_id or 'anonymous'}"),
        conversation_hash=_hash(f"{workspace_id}:{conversation_id}"),
        trace_id=trace_id,
        query_id=query_id,
        event_name="feedback_submitted",
        status="ACCEPTED",
        reason_code=feedback_type,
        properties_json={"feedback_type": feedback_type, "severity": severity},
    )
    try:
        session.add(event)
        session.commit()
    except SQLAlchemyError:
        session.rollback()


def record_product_interaction(
    session: Session,
    *,
    workspace_id: str,
    conversation_id: str,
    query_id: str,
    event_name: str,
    trace_id: str,
) -> ProductEvent:
    if event_name not in {"result_adopted", "result_corrected"}:
        raise ValueError("interaction event is invalid")
    run = session.get(QueryRun, query_id)
    if run is None or run.workspace_id != workspace_id:
        raise ValueError("query does not belong to workspace")
    existing = session.scalar(
        select(ProductEvent).where(
            ProductEvent.workspace_id == workspace_id,
            ProductEvent.query_id == query_id,
            ProductEvent.event_name == event_name,
        )
    )
    if existing is not None:
        return existing
    event = ProductEvent(
        event_id=f"evt_{uuid.uuid4().hex[:24]}",
        workspace_id=workspace_id,
        actor_hash=_hash(f"{workspace_id}:{run.operator_id}"),
        conversation_hash=_hash(f"{workspace_id}:{conversation_id}"),
        trace_id=trace_id,
        query_id=query_id,
        event_name=event_name,
        status="RECORDED",
        reason_code="EXPLICIT_USER_ACTION",
        properties_json={},
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def record_governance_event(
    session: Session,
    *,
    workspace_id: str,
    trace_id: str,
    event_name: str,
    status: str,
    properties: dict[str, Any],
) -> None:
    if event_name not in {"badcase_closure_validated", "metric_version_published"}:
        raise ValueError("governance event is invalid")
    event = ProductEvent(
        event_id=f"evt_{uuid.uuid4().hex[:24]}",
        workspace_id=workspace_id,
        actor_hash=_hash(f"{workspace_id}:{get_settings().default_operator_id}"),
        conversation_hash=_hash(f"{workspace_id}:metric_governance"),
        trace_id=trace_id,
        query_id=None,
        event_name=event_name,
        status=status,
        reason_code=str(properties.get("feedback_id") or ""),
        properties_json=properties,
    )
    try:
        session.add(event)
        session.commit()
    except SQLAlchemyError:
        session.rollback()


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * fraction) - 1]


def operations_summary(session: Session, workspace_id: str, window_days: int) -> dict[str, Any]:
    retention_days = get_settings().analytics_retention_days
    if window_days < 1 or window_days > retention_days:
        raise ValueError(f"window_days must be between 1 and {retention_days}")
    since = datetime.now(UTC) - timedelta(days=window_days)
    rows = session.scalars(
        select(ProductEvent).where(
            ProductEvent.workspace_id == workspace_id,
            ProductEvent.created_at >= since,
        )
    ).all()
    by_name = Counter(row.event_name for row in rows)
    status_rows = [row for row in rows if row.event_name == "status_decided"]
    statuses = Counter(row.status for row in status_rows)
    total_latencies = [row.duration_ms for row in status_rows if row.duration_ms is not None]
    execution_rows = [row for row in rows if row.event_name == "query_executed"]
    execution_latencies = [row.duration_ms for row in execution_rows if row.duration_ms is not None]
    retrieval_rows = [row for row in rows if row.event_name == "retrieval_completed"]
    estimated_rows = sum(int(row.properties_json.get("estimated_rows") or 0) for row in execution_rows)
    submitted = by_name["question_submitted"]
    traffic_counts = Counter(
        str(row.properties_json.get("traffic_class") or "unknown")
        for row in rows
        if row.event_name == "question_submitted"
    )
    return {
        "status": "SUCCESS",
        "workspace_id": workspace_id,
        "window_days": window_days,
        "retention_days": retention_days,
        "event_count": len(rows),
        "traffic_counts": dict(traffic_counts),
        "data_note": "当前数据包含本地自动测试与发布回归流量，不能表述为真实生产用户数据。",
        "funnel": {
            "submitted": submitted,
            "clarified": statuses["CLARIFY"],
            "accepted_for_execution": statuses["SUCCESS"],
            "executed": by_name["query_executed"],
            "reflection_passed": sum(
                row.event_name == "answer_rendered" and row.status == "PASS" for row in rows
            ),
            "feedback_received": by_name["feedback_submitted"],
            "adopted": by_name["result_adopted"],
            "manually_corrected": by_name["result_corrected"],
            "adoption_note": "采用与人工修正只统计用户显式点击，不由页面浏览或执行成功推断。",
        },
        "quality": {
            "status_counts": dict(statuses),
            "execution_success_rate": round(by_name["query_executed"] / submitted, 4)
            if submitted
            else 0.0,
            "reflection_pass_rate": round(
                sum(row.event_name == "answer_rendered" and row.status == "PASS" for row in rows)
                / by_name["answer_rendered"],
                4,
            )
            if by_name["answer_rendered"]
            else 0.0,
        },
        "latency_ms": {
            "end_to_end": {
                "average": round(statistics.fmean(total_latencies), 2) if total_latencies else 0,
                "p50": round(statistics.median(total_latencies), 2) if total_latencies else 0,
                "p95": _percentile(total_latencies, 0.95),
            },
            "execution": {
                "average": round(statistics.fmean(execution_latencies), 2)
                if execution_latencies
                else 0,
                "p50": round(statistics.median(execution_latencies), 2)
                if execution_latencies
                else 0,
                "p95": _percentile(execution_latencies, 0.95),
            },
        },
        "model_usage": {
            "retrieval_events": len(retrieval_rows),
            "embedding_used": sum(bool(row.properties_json.get("embedding_used")) for row in retrieval_rows),
            "reranker_used": sum(bool(row.properties_json.get("reranker_used")) for row in retrieval_rows),
            "estimated_rows_scanned": estimated_rows,
            "currency_cost": None,
            "cost_note": "当前 provider 未返回在线调用价格，暂不虚构货币成本。",
        },
        "governance": {
            "closure_validated": by_name["badcase_closure_validated"],
            "closure_passed": sum(
                row.event_name == "badcase_closure_validated" and row.status == "PASS"
                for row in rows
            ),
            "metric_versions_published": by_name["metric_version_published"],
        },
        "privacy": {
            "stores_question_text": False,
            "stores_sql_or_results": False,
            "actor_and_conversation": "sha256",
        },
    }
