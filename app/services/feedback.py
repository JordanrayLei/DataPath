from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import QueryRun, UserFeedback
from app.schemas.chatbi import (
    FeedbackItem,
    FeedbackListResponse,
    FeedbackStatusUpdateResponse,
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
)


REGRESSION_CANDIDATE_TYPES = {
    "METRIC_WRONG",
    "DATA_WRONG",
    "INTERPRETATION_UNTRUSTED",
    "CHART_WRONG",
    "PERMISSION_ISSUE",
}


class FeedbackError(ValueError):
    pass


def feedback_item(row: UserFeedback) -> FeedbackItem:
    return FeedbackItem(
        feedback_id=row.feedback_id,
        workspace_id=row.workspace_id,
        conversation_id=row.conversation_id,
        operator_id=row.operator_id,
        query_id=row.query_id,
        user_query=row.user_query,
        feedback_type=row.feedback_type,
        severity=row.severity,
        message=row.message,
        expected_behavior=row.expected_behavior,
        status=row.status,
        regression_candidate=row.regression_candidate,
        created_at=row.created_at,
        page_context=row.page_context,
        snapshot=row.snapshot_json,
    )


def build_query_snapshot(run: QueryRun | None) -> dict[str, Any]:
    if run is None:
        return {}
    return {
        "query_id": run.query_id,
        "workspace_id": run.workspace_id,
        "operator_id": run.operator_id,
        "status": run.status,
        "dsl_hash": run.dsl_hash,
        "sql_fingerprint": run.sql_fingerprint,
        "metric_versions": run.metric_versions,
        "lineage": run.lineage_json,
        "estimated_cost": run.estimated_cost,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "executed_at": run.executed_at.isoformat() if run.executed_at else None,
    }


def submit_feedback(
    session: Session,
    payload: FeedbackSubmitRequest,
    request_id: str,
    trace_id: str,
) -> FeedbackSubmitResponse:
    run = session.get(QueryRun, payload.query_id) if payload.query_id else None
    if payload.query_id and run is None:
        raise FeedbackError("query_id does not exist")
    if run is not None and run.workspace_id != payload.workspace_id:
        raise FeedbackError("query does not belong to workspace")

    regression_candidate = bool(
        payload.query_id and payload.feedback_type in REGRESSION_CANDIDATE_TYPES
    )
    feedback_id = f"fb_{uuid.uuid4().hex[:24]}"
    feedback = UserFeedback(
        feedback_id=feedback_id,
        workspace_id=payload.workspace_id,
        conversation_id=payload.conversation_id,
        operator_id=run.operator_id if run is not None else None,
        query_id=payload.query_id,
        user_query=payload.user_query,
        feedback_type=payload.feedback_type,
        severity=payload.severity,
        message=payload.message,
        expected_behavior=payload.expected_behavior,
        page_context=payload.page_context,
        snapshot_json=build_query_snapshot(run),
        status="OPEN",
        regression_candidate=regression_candidate,
    )
    session.add(feedback)
    session.commit()

    return FeedbackSubmitResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="ACCEPTED",
        feedback_id=feedback_id,
        query_id=payload.query_id,
        feedback_type=payload.feedback_type,
        severity=payload.severity,
        regression_candidate=regression_candidate,
        message=(
            "反馈已记录，并进入回归集候选。"
            if regression_candidate
            else "反馈已记录，等待产品确认。"
        ),
    )


def list_feedback(
    session: Session,
    request_id: str,
    trace_id: str,
    workspace_id: str = "demo",
    feedback_status: str = "ALL",
    limit: int = 50,
) -> FeedbackListResponse:
    if limit < 1 or limit > 200:
        raise FeedbackError("limit must be between 1 and 200")
    allowed_statuses = {"ALL", "OPEN", "CONFIRMED", "FIXED", "WONT_FIX"}
    if feedback_status not in allowed_statuses:
        raise FeedbackError("feedback status is invalid")

    filters = [UserFeedback.workspace_id == workspace_id]
    if feedback_status != "ALL":
        filters.append(UserFeedback.status == feedback_status)

    rows = session.scalars(
        select(UserFeedback)
        .where(*filters)
        .order_by(desc(UserFeedback.created_at))
        .limit(limit)
    ).all()
    total = session.scalar(select(func.count()).select_from(UserFeedback).where(*filters)) or 0
    count_rows = session.execute(
        select(UserFeedback.status, func.count())
        .where(UserFeedback.workspace_id == workspace_id)
        .group_by(UserFeedback.status)
    ).all()
    status_counts = {status: int(count) for status, count in count_rows}

    return FeedbackListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        items=[feedback_item(row) for row in rows],
        total=int(total),
        status_counts=status_counts,
    )


def update_feedback_status(
    session: Session,
    feedback_id: str,
    next_status: str,
    request_id: str,
    trace_id: str,
) -> FeedbackStatusUpdateResponse:
    row = session.get(UserFeedback, feedback_id)
    if row is None:
        raise FeedbackError("feedback_id does not exist")
    if next_status not in {"OPEN", "CONFIRMED", "FIXED", "WONT_FIX"}:
        raise FeedbackError("feedback status is invalid")
    row.status = next_status
    session.commit()
    session.refresh(row)
    return FeedbackStatusUpdateResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        feedback=feedback_item(row),
        message=f"反馈状态已更新为 {next_status}。",
    )
