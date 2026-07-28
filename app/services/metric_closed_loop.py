from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import GoldenQuestion, Metric, MetricDimension, MetricDraft, MetricVersion, UserFeedback
from app.schemas.chatbi import (
    GoldenQuestionCreateFromFeedbackRequest,
    MetricClosureValidationRequest,
    MetricClosureValidationResponse,
)
from app.services.bm25_retrieval import bm25_relevance_scores
from app.services.golden_questions import create_golden_question_from_feedback
from app.services.metric_management import draft_fingerprint, validate_definition
from app.services.metric_retrieval import (
    MetricRecord,
    explicit_match_lengths,
    load_metric_records,
    metric_search_document,
    score_term,
)
from app.services.product_analytics import record_governance_event


class MetricClosureError(ValueError):
    pass


def _draft_record(draft: MetricDraft, version: int) -> MetricRecord:
    return MetricRecord(
        metric=SimpleNamespace(
            id=draft.metric_id,
            name=draft.name,
            description=draft.description,
            metric_type=draft.metric_type,
            unit=draft.unit,
        ),
        version=SimpleNamespace(version=version),
        aliases=tuple(str(item) for item in (draft.aliases_json or [])),
        positive_examples=tuple(str(item) for item in (draft.positive_examples_json or [])),
        negative_examples=tuple(str(item) for item in (draft.negative_examples_json or [])),
    )


def _candidate_records(session: Session, draft: MetricDraft) -> list[MetricRecord]:
    records = [
        record
        for record in load_metric_records(session, draft.business_domain_id)
        if record.metric.id != draft.metric_id
    ]
    current = session.scalar(
        select(MetricVersion.version)
        .where(MetricVersion.metric_id == draft.metric_id)
        .order_by(MetricVersion.version.desc())
        .limit(1)
    )
    records.append(_draft_record(draft, int(current or 0) + 1))
    return records


def lexical_decision(query: str, records: list[MetricRecord]) -> dict[str, Any]:
    explicit_lengths = explicit_match_lengths(query, records)
    longest_explicit = max(explicit_lengths.values(), default=0)
    bm25_scores = bm25_relevance_scores(
        query, [metric_search_document(record) for record in records]
    )
    scored: list[tuple[float, list[str], MetricRecord]] = []
    for index, record in enumerate(records):
        score, sources = score_term(query, record)
        explicit_length = explicit_lengths.get(record.metric.id, 0)
        if explicit_length and explicit_length == longest_explicit:
            score = max(score, 0.995)
            sources = [*sources, "longest_explicit_match"]
        elif explicit_length:
            score = min(score, 0.88)
            sources = [*sources, "shorter_explicit_match"]
        bm25_score = bm25_scores[index]
        if bm25_score > 0:
            score = max(score, 0.45 + bm25_score * 0.35)
            sources = [*sources, "bm25"]
        if score >= 0.45:
            scored.append((round(score, 4), list(dict.fromkeys(sources)), record))
    scored.sort(key=lambda item: (-item[0], item[2].metric.id))
    top = scored[0] if scored else None
    runner_up = scored[1] if len(scored) > 1 else None
    if top is None:
        gate_status = "REJECT"
        selected_metric_id = None
    else:
        margin = top[0] - (runner_up[0] if runner_up else 0)
        governed_example_match = "positive_example" in top[1] and top[0] >= 0.86
        if runner_up and margin < 0.08 and not governed_example_match:
            gate_status = "CLARIFY"
            selected_metric_id = None
        elif top[0] >= 0.90:
            gate_status = "PASS"
            selected_metric_id = top[2].metric.id
        elif top[0] >= 0.70:
            gate_status = "LLM_DISAMBIGUATE"
            selected_metric_id = top[2].metric.id
        else:
            gate_status = "CLARIFY"
            selected_metric_id = None
    return {
        "gate_status": gate_status,
        "selected_metric_id": selected_metric_id,
        "score": top[0] if top else 0.0,
        "margin": round(top[0] - (runner_up[0] if runner_up else 0), 4) if top else 0.0,
        "sources": top[1] if top else [],
        "candidates": [
            {"metric_id": record.metric.id, "score": score, "sources": sources}
            for score, sources, record in scored[:5]
        ],
    }


def _matches_expected(decision: dict[str, Any], expected_status: str, expected_metric_id: str | None) -> bool:
    if expected_status == "SUCCESS":
        return decision["gate_status"] in {"PASS", "LLM_DISAMBIGUATE"} and decision[
            "selected_metric_id"
        ] == expected_metric_id
    if expected_status == "CLARIFY":
        return decision["gate_status"] == "CLARIFY"
    if expected_status == "REJECT":
        return decision["gate_status"] == "REJECT"
    return False


def _semantic_only_change(session: Session, draft: MetricDraft) -> tuple[bool, list[str]]:
    version = session.scalar(
        select(MetricVersion)
        .where(MetricVersion.metric_id == draft.metric_id, MetricVersion.status == "PUBLISHED")
        .order_by(MetricVersion.version.desc())
        .limit(1)
    )
    if version is None:
        return True, []
    metric = session.get(Metric, draft.metric_id)
    current_dimensions = set(
        session.scalars(
            select(MetricDimension.dimension_id).where(
                MetricDimension.metric_id == draft.metric_id
            )
        ).all()
    )
    changes = []
    comparisons = {
        "calculation formula": version.expression_json == draft.expression_json,
        "semantic model": version.semantic_model_id == draft.semantic_model_id,
        "time dimension": version.time_dimension_id == draft.time_dimension_id,
        "available dimensions": current_dimensions == set(draft.dimension_ids_json or []),
        "metric type": bool(metric and metric.metric_type == draft.metric_type),
        "unit": bool(metric and metric.unit == draft.unit),
    }
    changes.extend(label for label, unchanged in comparisons.items() if not unchanged)
    return not changes, changes


def validate_metric_closure(
    session: Session,
    metric_id: str,
    payload: MetricClosureValidationRequest,
    request_id: str,
    trace_id: str,
) -> MetricClosureValidationResponse:
    if payload.workspace_id != "demo":
        raise MetricClosureError("workspace is not allowed")
    draft = session.scalar(select(MetricDraft).where(MetricDraft.metric_id == metric_id))
    if draft is None:
        raise MetricClosureError("save the metric draft before running closure validation")
    feedback = session.get(UserFeedback, payload.feedback_id)
    if feedback is None or feedback.workspace_id != payload.workspace_id:
        raise MetricClosureError("feedback does not exist in this workspace")
    if feedback.status not in {"CONFIRMED", "FIXED"}:
        raise MetricClosureError("confirm the Bad Case before closure validation")
    if payload.expected_metric_id and payload.expected_metric_id != metric_id:
        raise MetricClosureError("the expected metric must match the draft being validated")

    validation_payload = GoldenQuestionCreateFromFeedbackRequest(
        biz_domain=payload.biz_domain,
        expected_status=payload.expected_status,
        expected_metric_id=payload.expected_metric_id,
        expected_intent=payload.expected_intent,
        expected_dimension_id=payload.expected_dimension_id,
        expected_chart_type=payload.expected_chart_type,
        expected_row_count=payload.expected_row_count,
        expected_reflection_status=payload.expected_reflection_status,
        expected_notes=payload.expected_notes,
    )
    golden_response = create_golden_question_from_feedback(
        session, payload.feedback_id, validation_payload, request_id, trace_id
    )
    golden = golden_response.golden_question
    records = _candidate_records(session, draft)
    candidate = lexical_decision(feedback.user_query, records)
    target_passed = _matches_expected(
        candidate, payload.expected_status, payload.expected_metric_id
    )

    active_rows = session.scalars(
        select(GoldenQuestion).where(
            GoldenQuestion.workspace_id == payload.workspace_id,
            GoldenQuestion.status == "ACTIVE",
            GoldenQuestion.expected_metric_id == metric_id,
        )
    ).all()
    regression_cases = []
    for row in active_rows:
        decision = lexical_decision(row.user_query, records)
        passed = _matches_expected(decision, row.expected_status, row.expected_metric_id)
        regression_cases.append(
            {
                "golden_id": row.golden_id,
                "expected_metric_id": row.expected_metric_id,
                "selected_metric_id": decision["selected_metric_id"],
                "gate_status": decision["gate_status"],
                "passed": passed,
            }
        )
    regression_passed = sum(bool(item["passed"]) for item in regression_cases)
    semantic_only, unsupported_changes = _semantic_only_change(session, draft)
    alias_collision_rows = (draft.validation_json or {}).get("alias_conflicts") or []
    checks = [
        {"id": "definition_valid", "passed": bool(validate_definition(session, validation_payload_to_draft(draft))["valid"]), "detail": "公式、模型和维度结构校验通过"},
        {"id": "operator_contract", "passed": True, "detail": "Golden 期望由工作人员显式确认"},
        {"id": "target_badcase", "passed": target_passed, "detail": f"候选指标={candidate['selected_metric_id'] or '-'}，状态={candidate['gate_status']}"},
        {"id": "affected_regression", "passed": regression_passed == len(regression_cases), "detail": f"{regression_passed}/{len(regression_cases)} 个同域指标 Golden 语义回归通过"},
        {
            "id": "semantic_only_scope",
            "passed": semantic_only,
            "detail": (
                "本闭环门禁覆盖名称、定义、别名及正反向问法变更"
                if semantic_only
                else "以下变更需要结果 Oracle，当前禁止仅靠语义预检发布：" + "、".join(unsupported_changes)
            ),
        },
        {
            "id": "alias_conflicts",
            "passed": not alias_collision_rows,
            "detail": (
                "指标名称和别名未与其他已发布指标冲突"
                if not alias_collision_rows
                else "存在冲突：" + "；".join(str(item.get("message") or item) for item in alias_collision_rows)
            ),
        },
    ]
    passed = all(bool(check["passed"]) for check in checks)
    gate = {
        "status": "PASS" if passed else "FAIL",
        "feedback_id": payload.feedback_id,
        "draft_fingerprint": draft_fingerprint(draft),
        "validated_at": golden.updated_at.isoformat(),
        "checks": checks,
        "target": candidate,
        "regression_total": len(regression_cases),
        "regression_passed": regression_passed,
    }
    draft.validation_json = {**(draft.validation_json or {}), "closure_gate": gate}
    session.commit()
    record_governance_event(
        session,
        workspace_id=payload.workspace_id,
        trace_id=trace_id,
        event_name="badcase_closure_validated",
        status="PASS" if passed else "FAIL",
        properties={
            "feedback_id": payload.feedback_id,
            "metric_id": metric_id,
            "target_passed": target_passed,
            "regression_total": len(regression_cases),
            "regression_passed": regression_passed,
            "publish_ready": passed,
        },
    )
    return MetricClosureValidationResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="PASS" if passed else "FAIL",
        feedback_id=payload.feedback_id,
        metric_id=metric_id,
        publish_ready=passed,
        checks=checks,
        baseline={
            "selected_metric_ids": sorted((feedback.snapshot_json or {}).get("metric_versions", {}).keys()),
            "status": (feedback.snapshot_json or {}).get("status"),
        },
        candidate=candidate,
        regression={
            "total": len(regression_cases),
            "passed": regression_passed,
            "failed": len(regression_cases) - regression_passed,
            "cases": regression_cases,
            "scope": "metric retrieval semantics for active Golden questions in the same domain",
        },
        golden_question=golden,
        message=(
            "闭环门禁通过，可以发布指标新版本。"
            if passed
            else "闭环门禁未通过，指标版本尚不可发布。"
        ),
    )


def validation_payload_to_draft(draft: MetricDraft):
    from app.schemas.chatbi import MetricDraftUpsertRequest

    return MetricDraftUpsertRequest(
        workspace_id="demo",
        metric_id=draft.metric_id,
        business_domain_id=draft.business_domain_id,
        name=draft.name,
        description=draft.description,
        metric_type=draft.metric_type,
        unit=draft.unit,
        owner=draft.owner,
        aliases=draft.aliases_json,
        positive_examples=draft.positive_examples_json,
        negative_examples=draft.negative_examples_json,
        semantic_model_id=draft.semantic_model_id,
        expression=draft.expression_json,
        default_aggregation=draft.default_aggregation,
        time_dimension_id=draft.time_dimension_id,
        dimension_ids=draft.dimension_ids_json,
    )
