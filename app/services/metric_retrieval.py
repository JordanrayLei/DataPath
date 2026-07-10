from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Metric, MetricVersion
from app.schemas.chatbi import (
    MetricCandidate,
    MetricMentionDecision,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
)

DEMO_REFERENCE_DATE = "2026-07-09"
DEMO_TIMEZONE = "Asia/Shanghai"
DEMO_LATEST_DATA_DATE = "2026-06-30"
DEMO_LATEST_COMPLETE_MONTH = "2026-06"
DEMO_RECENT_YEAR_START = "2025-07-01"
DEMO_RECENT_YEAR_END = "2026-06-30"


@dataclass(frozen=True)
class MetricRecord:
    metric: Metric
    version: MetricVersion
    aliases: tuple[str, ...]


def load_metric_records(session: Session, domain: str) -> list[MetricRecord]:
    rows = session.execute(
        select(Metric, MetricVersion)
        .join(MetricVersion, MetricVersion.metric_id == Metric.id)
        .options(selectinload(Metric.aliases))
        .where(
            Metric.business_domain_id == domain,
            Metric.status == "PUBLISHED",
            MetricVersion.status == "PUBLISHED",
        )
        .order_by(Metric.id, MetricVersion.version.desc())
    ).all()
    latest: dict[str, MetricRecord] = {}
    for metric, version in rows:
        latest.setdefault(
            metric.id,
            MetricRecord(metric, version, tuple(alias.alias for alias in metric.aliases)),
        )
    return list(latest.values())


def score_term(term: str, record: MetricRecord) -> tuple[float, list[str]]:
    normalized = term.strip().casefold()
    if not normalized:
        return 0.0, []
    name = record.metric.name.casefold()
    aliases = [alias.casefold() for alias in record.aliases]
    if normalized == name:
        return 0.99, ["exact_name"]
    if normalized in aliases:
        return 0.96, ["alias"]
    if normalized in name or name in normalized:
        return 0.86, ["exact_name"]
    if any(normalized in alias or alias in normalized for alias in aliases):
        return 0.84, ["alias"]
    similarity = max(
        [SequenceMatcher(None, normalized, name).ratio()]
        + [SequenceMatcher(None, normalized, alias).ratio() for alias in aliases]
    )
    if similarity >= 0.60:
        return round(similarity * 0.75, 4), ["context"]
    return 0.0, []


def infer_mentions(request: MetricRetrieveRequest, records: list[MetricRecord]) -> list[str]:
    mentions = [item.strip() for item in request.preprocess.metric_mentions if item.strip()]
    if mentions:
        return list(dict.fromkeys(mentions))

    query = request.normalized_query.casefold()
    discovered: list[str] = []
    terms = sorted(
        {
            value
            for record in records
            for value in (record.metric.name, *record.aliases)
            if value
        },
        key=len,
        reverse=True,
    )
    for term in terms:
        if term.casefold() in query and not any(term in existing for existing in discovered):
            discovered.append(term)
    return discovered[:10]


def build_time_resolution_hint(request: MetricRetrieveRequest) -> dict:
    """Return semantic-layer time hints for downstream DSL generation.

    The demo warehouse is seeded around the latest complete month. Dify's LLM
    nodes should treat this response as authoritative metric context, so
    relative windows such as "最近一年" resolve to a populated data range instead
    of drifting to a model-internal historical date.
    """

    requested_text = " ".join(
        [
            request.query,
            request.normalized_query,
            request.preprocess.time_text,
            " ".join(request.preprocess.dimension_mentions),
        ]
    ).lower()
    looks_monthly = any(token in requested_text for token in ["每月", "月度", "按月", "monthly"])
    looks_recent_year = any(
        token in requested_text
        for token in ["最近一年", "近一年", "过去一年", "last year", "recent year", "last 12 months"]
    )

    return {
        "source": "metric_retrieval",
        "reference_date": DEMO_REFERENCE_DATE,
        "timezone": DEMO_TIMEZONE,
        "warehouse_data_window": {
            "latest_data_date": DEMO_LATEST_DATA_DATE,
            "latest_complete_month": DEMO_LATEST_COMPLETE_MONTH,
            "note": "Demo fact tables are populated through the latest complete month only.",
        },
        "detected_time_need": {
            "looks_recent_year": looks_recent_year,
            "looks_monthly": looks_monthly,
        },
        "relative_time_policy": {
            "recent_year_monthly_default": {
                "applies_when": "User asks 最近一年/近一年/过去一年/last 12 months without an explicit historical year.",
                "start": DEMO_RECENT_YEAR_START,
                "end": DEMO_RECENT_YEAR_END,
                "timezone": DEMO_TIMEZONE,
                "required_intent": "trend_query",
                "required_dimension_id": "D_MONTH",
                "required_sort": [{"field_id": "D_MONTH", "direction": "asc"}],
                "recommended_limit": 100,
            }
        },
    }


def build_dsl_generation_constraints(request: MetricRetrieveRequest) -> list[str]:
    constraints = [
        (
            "When the user asks 最近一年/近一年/过去一年/last 12 months and does not name "
            f"an explicit historical year, generate time_range.start={DEMO_RECENT_YEAR_START} "
            f"and time_range.end={DEMO_RECENT_YEAR_END}; do not use 2023-04-01~2024-03-31."
        ),
        (
            "When the user asks 每月/月度/按月/monthly, generate intent=trend_query, "
            'dimensions=[{"dimension_id":"D_MONTH"}], sort D_MONTH ascending, and limit=100.'
        ),
        "Use only metric_id and metric_version returned by this metric retrieval response.",
    ]
    if request.preprocess.time_start and request.preprocess.time_end:
        constraints.append(
            "If preprocess time_start/time_end conflict with warehouse_data_window or relative_time_policy, "
            "prefer the metric retrieval time_resolution policy."
        )
    return constraints


def retrieve_metrics(
    session: Session,
    request: MetricRetrieveRequest,
    request_id: str,
    trace_id: str,
) -> MetricRetrieveResponse:
    records = load_metric_records(session, request.biz_domain)
    mentions = infer_mentions(request, records)
    decisions: list[MetricMentionDecision] = []
    statuses: list[str] = []

    for mention in mentions:
        scored = []
        for record in records:
            score, sources = score_term(mention, record)
            if score >= 0.45:
                scored.append((score, sources, record))
        scored.sort(key=lambda item: (-item[0], item[2].metric.id))
        scored = scored[:5]

        candidates = [
            MetricCandidate(
                metric_id=record.metric.id,
                metric_version=record.version.version,
                display_name=record.metric.name,
                metric_type=record.metric.metric_type,
                unit=record.metric.unit,
                business_definition=record.metric.description,
                probability=score,
                retrieval_sources=sources,
                authorized=True,
            )
            for score, sources, record in scored
        ]

        if not candidates:
            status = "REJECT"
            selected_id = ""
            selected_version = None
            probability = 0.0
        else:
            top = candidates[0]
            margin = top.probability - (candidates[1].probability if len(candidates) > 1 else 0)
            if len(candidates) > 1 and margin < 0.08:
                status = "CLARIFY"
                selected_id = ""
                selected_version = None
            elif top.probability >= 0.90:
                status = "PASS"
                selected_id = top.metric_id
                selected_version = top.metric_version
            elif top.probability >= 0.70:
                status = "LLM_DISAMBIGUATE"
                selected_id = top.metric_id
                selected_version = top.metric_version
            else:
                status = "CLARIFY"
                selected_id = ""
                selected_version = None
            probability = top.probability

        statuses.append(status)
        decisions.append(
            MetricMentionDecision(
                text=mention,
                selected_metric_id=selected_id,
                selected_metric_version=selected_version,
                probability=probability,
                candidates=candidates,
            )
        )

    if not decisions or "REJECT" in statuses:
        gate_status = "REJECT"
        reasons = ["METRIC_NOT_FOUND"]
    elif "CLARIFY" in statuses:
        gate_status = "CLARIFY"
        reasons = ["AMBIGUOUS_METRIC"]
    elif "LLM_DISAMBIGUATE" in statuses:
        gate_status = "LLM_DISAMBIGUATE"
        reasons = ["HEURISTIC_CONFIDENCE_REQUIRES_DISAMBIGUATION"]
    else:
        gate_status = "PASS"
        reasons = ["EXACT_OR_ALIAS_MATCH"]

    return MetricRetrieveResponse(
        request_id=request_id,
        trace_id=trace_id,
        gate_status=gate_status,
        mentions=decisions,
        reason_codes=reasons,
        clarification_message=(
            "请选择正确的指标口径。" if gate_status == "CLARIFY" else ""
        ),
        time_resolution=build_time_resolution_hint(request),
        dsl_generation_constraints=build_dsl_generation_constraints(request),
    )
