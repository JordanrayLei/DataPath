from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import QueryRun, ResultProfile
from app.schemas.chatbi import (
    Finding,
    Interpretation,
    InterpretationGenerateRequest,
    InterpretationGenerateResponse,
)
from app.services.query_compiler import sha256_json


class InterpretationGenerationError(ValueError):
    pass


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def generate_interpretation(
    session: Session,
    payload: InterpretationGenerateRequest,
    request_id: str,
    trace_id: str,
) -> InterpretationGenerateResponse:
    run = session.scalar(select(QueryRun).where(QueryRun.query_id == payload.query_id))
    if run is None:
        raise InterpretationGenerationError("query_id does not exist")
    if run.workspace_id != payload.workspace_id:
        raise InterpretationGenerationError("query does not belong to workspace")
    if run.status != "SUCCEEDED":
        raise InterpretationGenerationError("query has not succeeded")
    if sha256_json(payload.dsl.model_dump(mode="json", exclude_none=True)) != run.dsl_hash:
        raise InterpretationGenerationError("DSL does not match the compiled query")

    stored_profile = session.scalar(
        select(ResultProfile).where(ResultProfile.query_id == payload.query_id)
    )
    if stored_profile is None:
        raise InterpretationGenerationError("query has no stored profile")
    if (
        payload.profile.profile_id != stored_profile.profile_id
        or payload.profile.query_id != payload.query_id
    ):
        raise InterpretationGenerationError("profile does not match query")

    display_name = (
        payload.profile.headline_metrics[0].display_name
        if payload.profile.headline_metrics
        else "查询结果"
    )
    title = f"{display_name}证据约束解读"

    findings = [
        Finding(text=evidence.statement, evidence_ids=[evidence.evidence_id])
        for evidence in payload.profile.evidence[:3]
    ]
    caveats = _dedupe(
        [
            *payload.profile.caveats,
            "以下结论仅基于本次查询返回的聚合数据和 Evidence，不代表因果归因。",
        ]
    )[:10]
    next_actions = [
        "可继续按地区、渠道或商品维度下钻，验证异常月份的结构性差异。",
        "如需形成运营动作建议，请补充活动日历、预算、库存等业务上下文。",
    ]

    return InterpretationGenerateResponse(
        request_id=request_id,
        trace_id=trace_id,
        interpretation=Interpretation(
            title=title,
            findings=findings,
            caveats=caveats,
            next_actions=next_actions,
        ),
    )
