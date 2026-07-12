from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import Metric, MetricSemanticProfile, MetricVersion
from app.schemas.chatbi import (
    MetricCandidate,
    MetricMentionDecision,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
)
from app.services.bm25_retrieval import bm25_relevance_scores
from app.services.metric_vector_index import search_metric_vectors
from app.services.reranker_provider import RerankerProviderError, get_reranker_provider

DEMO_REFERENCE_DATE = "2018-10-18"
DEMO_TIMEZONE = "Asia/Shanghai"
DEMO_LATEST_DATA_DATE = "2018-10-17"
DEMO_LATEST_COMPLETE_MONTH = "2018-09"
DEMO_RECENT_YEAR_START = "2017-10-01"
DEMO_RECENT_YEAR_END = "2018-09-30"


@dataclass(frozen=True)
class MetricRecord:
    metric: Metric
    version: MetricVersion
    aliases: tuple[str, ...]
    positive_examples: tuple[str, ...]
    negative_examples: tuple[str, ...]


def load_metric_records(session: Session, domain: str) -> list[MetricRecord]:
    rows = session.execute(
        select(Metric, MetricVersion)
        .join(MetricVersion, MetricVersion.metric_id == Metric.id)
        .options(selectinload(Metric.aliases), selectinload(Metric.semantic_profile))
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
            MetricRecord(
                metric,
                version,
                tuple(alias.alias for alias in metric.aliases),
                tuple(str(item) for item in ((metric.semantic_profile.positive_examples_json if metric.semantic_profile else []) or [])),
                tuple(str(item) for item in ((metric.semantic_profile.negative_examples_json if metric.semantic_profile else []) or [])),
            ),
        )
    return list(latest.values())


def score_term(term: str, record: MetricRecord) -> tuple[float, list[str]]:
    normalized = term.strip().casefold()
    if not normalized:
        return 0.0, []
    name = record.metric.name.casefold()
    aliases = [alias.casefold() for alias in record.aliases]
    positive_examples = [item.casefold() for item in record.positive_examples]
    negative_examples = [item.casefold() for item in record.negative_examples]
    if normalized == name:
        return 0.99, ["exact_name"]
    if normalized in aliases:
        return 0.96, ["alias"]
    if normalized in positive_examples:
        return 0.88, ["positive_example"]
    if normalized in name or name in normalized:
        return 0.995, ["exact_name"]
    if any(normalized in alias or alias in normalized for alias in aliases):
        return 0.91, ["alias"]
    if any(normalized in example or example in normalized for example in positive_examples):
        return 0.86, ["positive_example"]
    lexical_similarity = max(
        [SequenceMatcher(None, normalized, name).ratio()]
        + [SequenceMatcher(None, normalized, alias).ratio() for alias in aliases]
    )
    example_similarity = max(
        [SequenceMatcher(None, normalized, example).ratio() for example in positive_examples]
        or [0.0]
    )
    negative_similarity = max(
        [SequenceMatcher(None, normalized, example).ratio() for example in negative_examples]
        or [0.0]
    )
    score = lexical_similarity * 0.55 + example_similarity * 0.45
    sources = ["lexical"]
    if example_similarity >= 0.45:
        sources.append("positive_example")
    if negative_similarity >= 0.72:
        score -= 0.20
        sources.append("negative_example_penalty")
    if score >= 0.42:
        return round(max(0.0, min(score, 0.89)), 4), sources
    return 0.0, []


def metric_search_document(record: MetricRecord) -> str:
    return "\n".join(
        [
            f"指标名称：{record.metric.name}",
            f"业务定义：{record.metric.description}",
            f"别名：{'、'.join(record.aliases)}",
            f"典型问法：{'；'.join(record.positive_examples)}",
        ]
    )


def merge_scored_candidate(
    scored: list[tuple[float, list[str], MetricRecord]],
    record: MetricRecord,
    score: float,
    sources: list[str],
) -> None:
    existing = next((item for item in scored if item[2].metric.id == record.metric.id), None)
    if existing:
        scored.remove(existing)
        score = max(score, existing[0])
        sources = [*existing[1], *sources]
    scored.append((round(score, 4), list(dict.fromkeys(sources)), record))


def rerank_scored_candidates(
    query: str,
    scored: list[tuple[float, list[str], MetricRecord]],
) -> list[tuple[float, list[str], MetricRecord]]:
    settings = get_settings()
    ordered = sorted(scored, key=lambda item: (-item[0], item[2].metric.id))
    head = ordered[: settings.reranker_candidate_limit]
    if len(head) < 2:
        return ordered
    try:
        reranked = get_reranker_provider().rerank(
            query,
            [metric_search_document(item[2]) for item in head],
        )
    except RerankerProviderError:
        return ordered

    rerank_by_index = {item.index: item.relevance_score for item in reranked}
    fused = []
    for index, (base_score, sources, record) in enumerate(head):
        rerank_score = rerank_by_index.get(index, 0.0)
        fused_score = base_score * (1.0 - settings.reranker_weight) + rerank_score * settings.reranker_weight
        fused.append((round(fused_score, 4), [*sources, "reranker"], record))
    fused.extend(ordered[len(head) :])
    return sorted(fused, key=lambda item: (-item[0], item[2].metric.id))


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
    return discovered[:10] or [request.normalized_query]


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
            f"and time_range.end={DEMO_RECENT_YEAR_END}; use the latest complete Olist month."
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


def is_vector_scope_rejected(
    top_positive_similarity: float,
    scope_negative_similarity: float,
    scope_negative_threshold: float,
    scope_margin: float,
) -> bool:
    return (
        scope_negative_similarity >= scope_negative_threshold
        and scope_negative_similarity >= top_positive_similarity - scope_margin
    )


def retrieve_metrics(
    session: Session,
    request: MetricRetrieveRequest,
    request_id: str,
    trace_id: str,
) -> MetricRetrieveResponse:
    settings = get_settings()
    records = load_metric_records(session, request.biz_domain)
    mentions = infer_mentions(request, records)
    decisions: list[MetricMentionDecision] = []
    statuses: list[str] = []

    for mention in mentions:
        scored = []
        search_documents = [metric_search_document(record) for record in records]
        bm25_scores = bm25_relevance_scores(mention, search_documents)
        for record in records:
            score, sources = score_term(mention, record)
            if score >= 0.45:
                scored.append((score, sources, record))
        lexical_top = max((item[0] for item in scored), default=0.0)
        vector_used = False
        if lexical_top < 0.70:
            vector_result = search_metric_vectors(session, mention, request.biz_domain)
            vector_scores = vector_result.scores
            top_vector_similarity = max(
                (item.positive_similarity for item in vector_scores.values()),
                default=0.0,
            )
            scope_rejected = is_vector_scope_rejected(
                top_vector_similarity,
                vector_result.scope_negative_similarity,
                settings.vector_scope_negative_threshold,
                settings.vector_scope_margin,
            )
            if scope_rejected:
                scored = []
                vector_scores = {}
            elif top_vector_similarity < settings.vector_min_positive_similarity:
                vector_scores = {}
            else:
                vector_used = bool(vector_scores)
            for record_index, record in enumerate(records):
                vector_score = vector_scores.get(record.metric.id)
                bm25_score = bm25_scores[record_index] if vector_used else 0.0
                if vector_score is None and bm25_score <= 0:
                    continue
                existing = next(
                    (item for item in scored if item[2].metric.id == record.metric.id),
                    None,
                )
                lexical_score = existing[0] if existing else 0.0
                calibrated_vector = 0.0
                if vector_score is not None:
                    semantic_score = max(
                        0.0,
                        vector_score.positive_similarity - vector_score.negative_similarity * 0.20,
                    )
                    calibrated_vector = min(0.89, 0.55 + semantic_score * 0.40)
                calibrated_bm25 = 0.45 + bm25_score * 0.35 if bm25_score > 0 else 0.0
                combined = max(
                    lexical_score,
                    calibrated_vector,
                    calibrated_bm25,
                    lexical_score * 0.45 + calibrated_vector * 0.35 + calibrated_bm25 * 0.20,
                )
                sources = list(existing[1]) if existing else []
                if vector_score is not None:
                    sources.append("embedding")
                if bm25_score > 0:
                    sources.append("bm25")
                merge_scored_candidate(scored, record, combined, sources)
        if vector_used:
            scored = rerank_scored_candidates(mention, scored)
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
