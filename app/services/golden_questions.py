from __future__ import annotations

import uuid
from time import perf_counter
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import GoldenQuestion, QueryRun, UserFeedback
from app.schemas.chatbi import (
    ChatbiAskRequest,
    GoldenQuestionCaseResult,
    GoldenQuestionCreateFromFeedbackRequest,
    GoldenQuestionCreateResponse,
    GoldenQuestionEvaluationRequest,
    GoldenQuestionEvaluationResponse,
    GoldenQuestionItem,
    GoldenQuestionListResponse,
)
from app.services.chatbi_entrypoint import answer_chatbi_question


class GoldenQuestionError(ValueError):
    pass


def golden_question_item(row: GoldenQuestion) -> GoldenQuestionItem:
    return GoldenQuestionItem(
        golden_id=row.golden_id,
        workspace_id=row.workspace_id,
        source_feedback_id=row.source_feedback_id,
        query_id=row.query_id,
        user_query=row.user_query,
        biz_domain=row.biz_domain,
        expected_status=row.expected_status,
        expected_metric_id=row.expected_metric_id,
        expected_intent=row.expected_intent,
        expected_dimension_id=row.expected_dimension_id,
        expected_chart_type=row.expected_chart_type,
        expected_row_count=row.expected_row_count,
        expected_reflection_status=row.expected_reflection_status,
        expected_notes=row.expected_notes,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def first_metric_id(dsl: dict[str, Any]) -> str | None:
    metrics = dsl.get("metrics") or []
    if not metrics:
        return None
    metric_id = metrics[0].get("metric_id")
    return str(metric_id) if metric_id else None


def first_dimension_id(dsl: dict[str, Any]) -> str | None:
    dimensions = dsl.get("dimensions") or []
    if not dimensions:
        return None
    dimension_id = dimensions[0].get("dimension_id")
    return str(dimension_id) if dimension_id else None


def infer_chart_type(dsl: dict[str, Any], page_context: dict[str, Any]) -> str | None:
    explicit = page_context.get("chart_type") or (page_context.get("profile") or {}).get(
        "chart_spec", {}
    ).get("type")
    if explicit:
        return str(explicit)
    intent = dsl.get("intent")
    if intent == "trend_query":
        return "line"
    if intent == "ranking_query":
        return "bar"
    if intent == "aggregate_query":
        return "metric"
    return None


def infer_domain_from_metric(metric_id: str | None, fallback: str) -> str:
    if fallback in {"sales", "advertising"}:
        return fallback
    if metric_id and metric_id.startswith("M_AD_"):
        return "advertising"
    if metric_id and metric_id.startswith("M_SALES_"):
        return "sales"
    return "auto"


def infer_row_count(run: QueryRun | None) -> int | None:
    if run is None or run.result_json is None:
        return None
    row_count = run.result_json.get("row_count")
    if isinstance(row_count, int):
        return row_count
    rows = run.result_json.get("rows")
    return len(rows) if isinstance(rows, list) else None


def infer_reflection_status(page_context: dict[str, Any]) -> str | None:
    reflection = page_context.get("reflection")
    if isinstance(reflection, dict) and reflection.get("status"):
        return str(reflection["status"])
    return "PASS"


def create_golden_question_from_feedback(
    session: Session,
    feedback_id: str,
    payload: GoldenQuestionCreateFromFeedbackRequest,
    request_id: str,
    trace_id: str,
) -> GoldenQuestionCreateResponse:
    feedback = session.get(UserFeedback, feedback_id)
    if feedback is None:
        raise GoldenQuestionError("feedback_id does not exist")
    if feedback.status not in {"CONFIRMED", "FIXED"}:
        raise GoldenQuestionError("only CONFIRMED or FIXED feedback can become a golden question")
    if not feedback.regression_candidate:
        raise GoldenQuestionError("feedback is not a regression candidate")
    if not feedback.query_id:
        raise GoldenQuestionError("feedback has no query_id to replay")

    existing = session.scalar(
        select(GoldenQuestion).where(GoldenQuestion.source_feedback_id == feedback.feedback_id)
    )
    if existing is not None:
        return GoldenQuestionCreateResponse(
            request_id=request_id,
            trace_id=trace_id,
            status="SUCCESS",
            golden_question=golden_question_item(existing),
            created=False,
            message="Golden question already exists for this feedback.",
        )

    run = session.get(QueryRun, feedback.query_id)
    if run is None:
        raise GoldenQuestionError("feedback query_id does not exist")

    dsl = run.dsl_json or {}
    metric_id = first_metric_id(dsl)
    golden = GoldenQuestion(
        golden_id=f"gq_{uuid.uuid4().hex[:24]}",
        workspace_id=feedback.workspace_id,
        source_feedback_id=feedback.feedback_id,
        query_id=feedback.query_id,
        user_query=feedback.user_query,
        biz_domain=infer_domain_from_metric(metric_id, payload.biz_domain),
        expected_status=payload.expected_status,
        expected_metric_id=metric_id,
        expected_intent=dsl.get("intent"),
        expected_dimension_id=first_dimension_id(dsl),
        expected_chart_type=infer_chart_type(dsl, feedback.page_context or {}),
        expected_row_count=infer_row_count(run),
        expected_reflection_status=infer_reflection_status(feedback.page_context or {}),
        expected_notes=payload.expected_notes or feedback.expected_behavior,
        status="ACTIVE",
    )
    session.add(golden)
    session.commit()
    session.refresh(golden)
    return GoldenQuestionCreateResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        golden_question=golden_question_item(golden),
        created=True,
        message="Golden question was created from confirmed feedback.",
    )


def list_golden_questions(
    session: Session,
    request_id: str,
    trace_id: str,
    workspace_id: str = "demo",
    golden_status: str = "ACTIVE",
    limit: int = 50,
) -> GoldenQuestionListResponse:
    if limit < 1 or limit > 200:
        raise GoldenQuestionError("limit must be between 1 and 200")
    if golden_status not in {"ACTIVE", "ARCHIVED", "ALL"}:
        raise GoldenQuestionError("golden question status is invalid")

    filters = [GoldenQuestion.workspace_id == workspace_id]
    if golden_status != "ALL":
        filters.append(GoldenQuestion.status == golden_status)

    rows = session.scalars(
        select(GoldenQuestion)
        .where(*filters)
        .order_by(desc(GoldenQuestion.created_at))
        .limit(limit)
    ).all()
    total = session.scalar(select(func.count()).select_from(GoldenQuestion).where(*filters)) or 0
    count_rows = session.execute(
        select(GoldenQuestion.status, func.count())
        .where(GoldenQuestion.workspace_id == workspace_id)
        .group_by(GoldenQuestion.status)
    ).all()
    status_counts = {status: int(count) for status, count in count_rows}
    return GoldenQuestionListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        items=[golden_question_item(row) for row in rows],
        total=int(total),
        status_counts=status_counts,
    )


def observed_dimension(body: dict[str, Any]) -> str | None:
    dimensions = (body.get("dsl") or {}).get("dimensions") or []
    if not dimensions:
        return None
    dimension_id = dimensions[0].get("dimension_id")
    return str(dimension_id) if dimension_id else None


def compare_golden_question(row: GoldenQuestion, body: dict[str, Any], latency_ms: int) -> GoldenQuestionCaseResult:
    observed_metric_id = (body.get("selected_metric") or {}).get("metric_id")
    observed_intent = (body.get("dsl") or {}).get("intent")
    observed_chart_type = (body.get("profile") or {}).get("chart_spec", {}).get("type")
    observed_row_count = (body.get("execution") or {}).get("row_count")
    observed_reflection_status = (body.get("reflection") or {}).get("status")
    errors: list[str] = []

    checks = [
        ("status", row.expected_status, body.get("status")),
        ("metric", row.expected_metric_id, observed_metric_id),
        ("intent", row.expected_intent, observed_intent),
        ("dimension", row.expected_dimension_id, observed_dimension(body)),
        ("chart", row.expected_chart_type, observed_chart_type),
        ("row_count", row.expected_row_count, observed_row_count),
        ("reflection", row.expected_reflection_status, observed_reflection_status),
    ]
    for label, expected, observed in checks:
        if expected is not None and observed != expected:
            errors.append(f"{label} expected {expected}, got {observed}")

    return GoldenQuestionCaseResult(
        golden_id=row.golden_id,
        user_query=row.user_query,
        passed=not errors,
        errors=errors,
        latency_ms=latency_ms,
        observed_status=body.get("status"),
        observed_metric_id=observed_metric_id,
        observed_intent=observed_intent,
        observed_dimension_id=observed_dimension(body),
        observed_chart_type=observed_chart_type,
        observed_row_count=observed_row_count,
        observed_reflection_status=observed_reflection_status,
    )


def evaluate_golden_questions(
    session: Session,
    payload: GoldenQuestionEvaluationRequest,
    request_id: str,
    trace_id: str,
) -> GoldenQuestionEvaluationResponse:
    filters = [GoldenQuestion.workspace_id == payload.workspace_id]
    if payload.status != "ALL":
        filters.append(GoldenQuestion.status == payload.status)

    rows = session.scalars(
        select(GoldenQuestion)
        .where(*filters)
        .order_by(desc(GoldenQuestion.created_at))
        .limit(payload.limit)
    ).all()
    results: list[GoldenQuestionCaseResult] = []
    for row in rows:
        started = perf_counter()
        body = answer_chatbi_question(
            session,
            ChatbiAskRequest(
                query=row.user_query,
                workspace_id=row.workspace_id,
                conversation_id=f"golden_eval_{row.golden_id}",
                biz_domain=row.biz_domain if row.biz_domain in {"auto", "sales", "advertising"} else "auto",
                timezone="Asia/Shanghai",
            ),
            request_id,
            trace_id,
        ).model_dump(mode="json")
        latency_ms = int((perf_counter() - started) * 1000)
        results.append(compare_golden_question(row, body, latency_ms))

    total = len(results)
    passed = sum(1 for item in results if item.passed)
    status = "EMPTY" if total == 0 else "PASS" if passed == total else "FAIL"
    return GoldenQuestionEvaluationResponse(
        request_id=request_id,
        trace_id=trace_id,
        status=status,
        total=total,
        passed=passed,
        pass_rate=round(passed / total, 4) if total else 0,
        results=results,
    )
