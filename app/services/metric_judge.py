from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Dimension, Metric, MetricAlias, MetricDimension, MetricSemanticProfile, MetricVersion, SemanticEntity
from app.schemas.chatbi import MetricCandidate, MetricMentionDecision, MetricRetrieveRequest, MetricRetrieveResponse


class MetricJudgeError(RuntimeError):
    pass


class MetricJudgeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["SUCCESS", "CLARIFY", "REJECT"]
    selected_metric_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason_code: str = Field(min_length=1, max_length=100)
    matched_concepts: list[str] = Field(default_factory=list, max_length=20)
    conflicting_candidates: list[str] = Field(default_factory=list, max_length=5)
    missing_information: list[str] = Field(default_factory=list, max_length=10)
    clarification_question: str | None = Field(default=None, max_length=500)


@dataclass(frozen=True)
class MetricJudgeResult:
    output: MetricJudgeOutput
    provider: str
    model: str
    fallback: bool = False
    error_code: str = ""


class MetricJudgeProvider(Protocol):
    name: str

    def judge(self, payload: dict[str, Any]) -> MetricJudgeResult: ...


class DisabledMetricJudgeProvider:
    name = "disabled"

    def judge(self, payload: dict[str, Any]) -> MetricJudgeResult:
        return MetricJudgeResult(
            output=MetricJudgeOutput(
                decision="CLARIFY",
                selected_metric_id=None,
                confidence=0.0,
                reason_code="JUDGE_NOT_CONFIGURED",
                missing_information=["候选指标需要进一步确认"],
                clarification_question="请选择你希望使用的指标口径。",
            ),
            provider=self.name,
            model="",
            fallback=True,
            error_code="JUDGE_NOT_CONFIGURED",
        )


SYSTEM_PROMPT = """You are a constrained analytics metric judge.
Decide only whether the user's question uniquely matches one of the supplied candidates.
Never invent a metric, formula, dimension, capability, or SQL.
Judge the metric meaning independently from downstream query-shape support. Requested dimensions,
filters, joins, time grains, dirty-data conditions, and report/use-case wording are modifiers, not
reasons to reject a uniquely matching metric; deterministic DSL validation decides whether those
modifiers are executable. When exactly one candidate matches the core metric phrase, return SUCCESS
even if a governed join or downstream data-quality handling may be required.
Return SUCCESS only when exactly one candidate is semantically entailed and required information is sufficient.
Return CLARIFY when multiple candidates remain plausible or required business meaning is missing.
Return REJECT only when none of the candidates can answer the request.
selected_metric_id must be null unless decision is SUCCESS, and on SUCCESS it must be one supplied candidate id.
Use concise reason codes and a single actionable clarification question. Return JSON only."""


class HttpMetricJudgeProvider:
    name = "http_structured_metric_judge"

    def __init__(self, *, url: str, token: str, model: str, provider_name: str) -> None:
        self.url = url
        self.token = token
        self.model = model
        self.name = provider_name

    def judge(self, payload: dict[str, Any]) -> MetricJudgeResult:
        settings = get_settings()
        if not self.url:
            raise MetricJudgeError("metric judge URL is not configured")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request_body = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(
                timeout=settings.metric_judge_timeout_seconds,
                trust_env=False,
            ) as client:
                response = client.post(self.url, headers=headers, json=request_body)
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
            data = json.loads(content) if isinstance(content, str) else content
            output = MetricJudgeOutput.model_validate(data)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, ValidationError) as error:
            raise MetricJudgeError(f"metric judge request failed: {error}") from error
        return MetricJudgeResult(
            output=output,
            provider=self.name,
            model=self.model,
        )


def get_metric_judge_provider() -> MetricJudgeProvider:
    settings = get_settings()
    if settings.metric_judge_provider == "deepseek":
        return HttpMetricJudgeProvider(
            url=f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
            token=settings.deepseek_api_key,
            model=settings.deepseek_model,
            provider_name="deepseek_structured_metric_judge",
        )
    if settings.metric_judge_provider == "dashscope":
        return HttpMetricJudgeProvider(
            url=f"{settings.metric_judge_base_url.rstrip('/')}/chat/completions",
            token=settings.dashscope_api_key,
            model=settings.metric_judge_model,
            provider_name="dashscope_structured_metric_judge",
        )
    if settings.metric_judge_provider == "http":
        return HttpMetricJudgeProvider(
            url=settings.metric_judge_url,
            token=settings.metric_judge_token,
            model=settings.metric_judge_model,
            provider_name="http_structured_metric_judge",
        )
    return DisabledMetricJudgeProvider()


def _candidate_packet(session: Session, candidate: MetricCandidate) -> dict[str, Any]:
    metric = session.get(Metric, candidate.metric_id)
    version = session.scalar(
        select(MetricVersion).where(
            MetricVersion.metric_id == candidate.metric_id,
            MetricVersion.version == candidate.metric_version,
            MetricVersion.status == "PUBLISHED",
        )
    )
    if metric is None or version is None:
        raise MetricJudgeError("candidate metric version is no longer published")
    aliases = session.scalars(
        select(MetricAlias.alias).where(MetricAlias.metric_id == candidate.metric_id)
    ).all()
    profile = session.get(MetricSemanticProfile, candidate.metric_id)
    dimensions = session.execute(
        select(Dimension.id, Dimension.name)
        .join(MetricDimension, MetricDimension.dimension_id == Dimension.id)
        .where(MetricDimension.metric_id == candidate.metric_id)
        .order_by(Dimension.id)
    ).all()
    entity = session.scalar(
        select(SemanticEntity).where(
            SemanticEntity.semantic_model_id == version.semantic_model_id
        )
    )
    return {
        "metric_id": candidate.metric_id,
        "metric_version": candidate.metric_version,
        "name": candidate.display_name,
        "definition": candidate.business_definition,
        "metric_type": candidate.metric_type,
        "unit": candidate.unit,
        "formula": version.expression_json,
        "grain": entity.grain if entity else "",
        "aliases": list(aliases)[:10],
        "positive_examples": list((profile.positive_examples_json if profile else []) or [])[:8],
        "negative_examples": list((profile.negative_examples_json if profile else []) or [])[:8],
        "dimensions": [
            {"dimension_id": dimension_id, "name": name}
            for dimension_id, name in dimensions
        ],
        "retrieval_score": candidate.probability,
        "retrieval_sources": candidate.retrieval_sources,
    }


def build_metric_judge_payload(
    session: Session,
    request: MetricRetrieveRequest,
    mention: MetricMentionDecision,
) -> dict[str, Any]:
    return {
        "task": "select a unique metric or request clarification",
        "query": request.query,
        "normalized_query": request.normalized_query,
        "business_domain": request.biz_domain,
        "extracted_slots": {
            "time_text": request.preprocess.time_text,
            "time_start": request.preprocess.time_start,
            "time_end": request.preprocess.time_end,
            "dimensions": request.preprocess.dimension_mentions,
            "filters": [item.model_dump(mode="json") for item in request.preprocess.filter_mentions],
            "inherit_context": request.preprocess.inherit_context,
        },
        "candidates": [
            _candidate_packet(session, candidate) for candidate in mention.candidates[:5]
        ],
        "response_schema": MetricJudgeOutput.model_json_schema(),
    }


def _fail_closed(error_code: str) -> MetricJudgeResult:
    return MetricJudgeResult(
        output=MetricJudgeOutput(
            decision="CLARIFY",
            selected_metric_id=None,
            confidence=0.0,
            reason_code=error_code,
            missing_information=["指标裁判未能给出可验证的唯一结果"],
            clarification_question="请选择你希望使用的指标口径。",
        ),
        provider="fail_closed",
        model="",
        fallback=True,
        error_code=error_code,
    )


def adjudicate_metric_candidates(
    session: Session,
    request: MetricRetrieveRequest,
    retrieval: MetricRetrieveResponse,
    provider: MetricJudgeProvider | None = None,
) -> tuple[MetricRetrieveResponse, list[MetricJudgeResult]]:
    """Resolve uncertain retrievals while preserving deterministic gates."""

    if retrieval.gate_status in {"PASS", "REJECT"}:
        return retrieval, []
    if not retrieval.mentions or not any(item.candidates for item in retrieval.mentions):
        return retrieval, []

    judge = provider or get_metric_judge_provider()
    results: list[MetricJudgeResult] = []
    mentions: list[MetricMentionDecision] = []
    decisions: list[str] = []
    clarification = ""
    settings = get_settings()
    for mention in retrieval.mentions:
        if not mention.candidates:
            mentions.append(mention)
            decisions.append("CLARIFY")
            continue
        candidate_ids = {item.metric_id for item in mention.candidates}
        try:
            result = judge.judge(build_metric_judge_payload(session, request, mention))
        except MetricJudgeError:
            result = _fail_closed("JUDGE_PROVIDER_ERROR")
        output = result.output
        selected = next(
            (
                item
                for item in mention.candidates
                if item.metric_id == output.selected_metric_id
            ),
            None,
        )
        valid_success = (
            output.decision == "SUCCESS"
            and output.selected_metric_id in candidate_ids
            and selected is not None
            and output.confidence >= settings.metric_judge_min_confidence
        )
        if output.decision == "SUCCESS" and not valid_success:
            result = _fail_closed("JUDGE_INVALID_OR_LOW_CONFIDENCE_SUCCESS")
            output = result.output
            selected = None
        if valid_success and selected is not None:
            mentions.append(
                mention.model_copy(
                    update={
                        "selected_metric_id": selected.metric_id,
                        "selected_metric_version": selected.metric_version,
                        "probability": output.confidence,
                    }
                )
            )
            decisions.append("PASS")
        else:
            mentions.append(
                mention.model_copy(
                    update={"selected_metric_id": "", "selected_metric_version": None}
                )
            )
            decisions.append(output.decision)
            clarification = output.clarification_question or clarification
        results.append(result)

    if "REJECT" in decisions:
        gate_status = "REJECT"
    elif all(item == "PASS" for item in decisions):
        gate_status = "PASS"
    else:
        gate_status = "CLARIFY"
    reason_codes = [
        f"METRIC_JUDGE_{result.output.reason_code}" for result in results
    ] or retrieval.reason_codes
    diagnostics = {
        **retrieval.runtime_diagnostics,
        "metric_judge": {
            "invoked": True,
            "provider": results[0].provider if results else judge.name,
            "model": results[0].model if results else "",
            "fallback": any(item.fallback for item in results),
            "min_confidence": settings.metric_judge_min_confidence,
            "decisions": [item.output.model_dump(mode="json") for item in results],
        },
    }
    return (
        retrieval.model_copy(
            update={
                "gate_status": gate_status,
                "mentions": mentions,
                "reason_codes": reason_codes,
                "clarification_message": (
                    clarification or "请选择正确的指标口径。"
                    if gate_status == "CLARIFY"
                    else ""
                ),
                "runtime_diagnostics": diagnostics,
            }
        ),
        results,
    )
