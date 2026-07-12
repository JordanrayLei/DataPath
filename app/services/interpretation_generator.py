from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import QueryRun, ResultProfile
from app.schemas.chatbi import (
    Finding,
    Interpretation,
    InterpretationGenerateRequest,
    InterpretationGenerateResponse,
    ProfileResponse,
)
from app.services.query_compiler import sha256_json


class InterpretationGenerationError(ValueError):
    pass


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _format_percent(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _business_title(profile: ProfileResponse) -> str:
    display_name = (
        profile.headline_metrics[0].display_name
        if profile.headline_metrics
        else "查询结果"
    )

    if profile.chart_spec.type in {"bar", "grouped_bar", "stacked_bar"}:
        leading = min(profile.dimension_contributions, key=lambda item: item.rank, default=None)
        if leading is not None:
            share = _format_percent(leading.share * 100)
            return f"{leading.dimension_value}贡献最高，占比{share}%"

    if profile.trend_summary:
        trend = profile.trend_summary[0]
        if trend.direction == "flat":
            return f"{display_name}整体保持稳定"
        if trend.change_rate is not None:
            direction = "增长" if trend.direction == "up" else "下降"
            rate = _format_percent(abs(trend.change_rate))
            return f"{display_name}较期初{direction}{rate}%"

    if profile.evidence:
        return profile.evidence[0].statement.rstrip("。")
    return f"{display_name}查询结果"


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

    title = _business_title(payload.profile)

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
