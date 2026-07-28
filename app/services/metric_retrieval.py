from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import Metric, MetricSemanticProfile, MetricVersion, SemanticScopePolicy
from app.schemas.chatbi import (
    MetricCandidate,
    MetricMentionDecision,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
)
from app.services.bm25_retrieval import bm25_relevance_scores
from app.services.join_planner import expression_model_ids
from app.services.metric_vector_index import search_metric_vectors
from app.services.reranker_provider import RerankerProviderError, get_reranker_provider
from app.services.query_policy import (
    is_explicitly_staged_production_query,
    is_underspecified_metric_query,
)

DEFAULT_TIMEZONE = "Asia/Shanghai"


def _normalized_capability_phrase(value: str) -> str:
    return re.sub(r"[\s的之？?！!。,.，、：:;；()（）]+", "", value).casefold()


def matches_unpublished_metric_name(session: Session, domain: str, query: str) -> bool:
    """Prevent a published metric from substituting for a governed staged metric."""

    normalized_query = _normalized_capability_phrase(query)
    staged_names = session.scalars(
        select(Metric.name).where(
            Metric.business_domain_id == domain,
            Metric.status != "PUBLISHED",
        )
    ).all()
    return any(
        len(normalized_name) >= 4 and normalized_name in normalized_query
        for name in staged_names
        if (normalized_name := _normalized_capability_phrase(str(name)))
    )


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
    if name in normalized:
        return 0.98, ["name_in_query"]
    if any(alias in normalized for alias in aliases):
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


def explicit_match_lengths(term: str, records: list[MetricRecord]) -> dict[str, int]:
    """Return the longest governed name or alias explicitly present per metric."""

    normalized = term.strip().casefold()
    matches: dict[str, int] = {}
    for record in records:
        governed_terms = [record.metric.name, *record.aliases]
        lengths = [
            len(value.strip())
            for value in governed_terms
            if value.strip() and value.strip().casefold() in normalized
        ]
        if lengths:
            matches[record.metric.id] = max(lengths)
    return matches


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
    if len(reranked) != len(head):
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
    # A governed name/alias explicitly present in the user's full turn is
    # stronger evidence than an LLM-produced shortened mention.  For example,
    # "扣除退款后的净收入" must not be reduced to the ambiguous "净收入".
    if explicit_match_lengths(request.normalized_query, records):
        return [request.normalized_query]

    mentions = list(
        dict.fromkeys(
            item.strip()
            for item in request.preprocess.metric_mentions
            if item.strip()
        )
    )
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


def _last_query_context(request: MetricRetrieveRequest) -> dict:
    context = request.context.get("last_query_context", {})
    return context if isinstance(context, dict) else {}


def _query_explicit_metric_ids(
    query: str, records: list[MetricRecord]
) -> set[str]:
    """Find governed metric names/aliases explicitly written in this turn.

    LLM-extracted metric mentions are deliberately not used here: on a short
    follow-up such as "再按币种展示", preprocessors can infer a different metric
    even though the user did not change the metric at all.
    """

    return set(explicit_match_lengths(query, records))


def validated_inherited_metric(
    request: MetricRetrieveRequest, records: list[MetricRecord]
) -> MetricRecord | None:
    """Return the unique, still-published prior metric for an implicit follow-up."""

    if not request.preprocess.inherit_context:
        return None
    context = _last_query_context(request)
    if context.get("biz_domain") not in (None, "", request.biz_domain):
        return None
    metrics = context.get("metrics")
    if not isinstance(metrics, list) or len(metrics) != 1:
        return None
    inherited_id = metrics[0].get("metric_id") if isinstance(metrics[0], dict) else None
    record = next((item for item in records if item.metric.id == inherited_id), None)
    if record is None:
        return None
    explicit_ids = _query_explicit_metric_ids(request.normalized_query, records)
    if explicit_ids and explicit_ids != {inherited_id}:
        return None
    return record


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
    usage_only_monthly = bool(
        re.search(r"用于.{0,20}月度(?:复盘|报告|周报|会议)", requested_text)
    )
    looks_monthly = any(
        token in requested_text
        for token in ["每月", "按月", "月份", "月度趋势", "monthly trend"]
    ) and not usage_only_monthly
    looks_recent_year = any(
        token in requested_text
        for token in ["最近一年", "近一年", "过去一年", "last year", "recent year", "last 12 months"]
    )

    prior_time_range = _last_query_context(request).get("time_range")
    has_explicit_time = bool(
        request.preprocess.time_start
        or request.preprocess.time_end
        or request.preprocess.time_text.strip()
        or re.search(r"\b(?:19|20)\d{2}\b", requested_text)
        or looks_recent_year
    )
    inherited_time_range = (
        prior_time_range
        if request.preprocess.inherit_context
        and not has_explicit_time
        and isinstance(prior_time_range, dict)
        else None
    )
    return {
        "source": "validated_conversation_context" if inherited_time_range else "metric_retrieval",
        "timezone": DEFAULT_TIMEZONE,
        "detected_time_need": {
            "looks_recent_year": looks_recent_year,
            "looks_monthly": looks_monthly,
            "usage_only_monthly": usage_only_monthly,
        },
        "inherited_time_range": inherited_time_range,
        "relative_time_policy": {},
        "note": "Dates must come from the current request, governed source metadata, or validated conversation context.",
    }


def build_dsl_generation_constraints(request: MetricRetrieveRequest) -> list[str]:
    time_resolution = build_time_resolution_hint(request)
    constraints = [
        "Use only metric_id and metric_version returned by this metric retrieval response.",
        "Never invent a fixed demo date window; use the request, governed source metadata, or validated conversation context.",
    ]
    inherited_time_range = time_resolution.get("inherited_time_range")
    if inherited_time_range:
        constraints.append(
            "This follow-up omits an explicit time window: copy time_resolution.inherited_time_range exactly into DSL time_range."
        )
    if time_resolution["detected_time_need"].get("usage_only_monthly"):
        constraints.append(
            "用于某团队月度复盘/报告 describes report usage only: do not add D_MONTH or trend_query unless the user explicitly asks 按月/每月/逐月/月度趋势."
        )
    if time_resolution["detected_time_need"]["looks_monthly"]:
        constraints.append(
            "When the user asks 每月/月度/按月/monthly, generate intent=trend_query, "
            'dimensions=[{"dimension_id":"D_MONTH"}], sort D_MONTH ascending, and limit=100.'
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


def retrieval_runtime_diagnostics() -> dict:
    settings = get_settings()
    embedding_configured = settings.embedding_provider in {
        "local_char_ngram",
        "local_sentence_transformer",
    } or bool(settings.dashscope_api_key.strip())
    return {
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_configured": embedding_configured,
        "vector_min_positive_similarity": (
            settings.local_sentence_transformer_min_positive_similarity
            if settings.embedding_provider == "local_sentence_transformer"
            else settings.vector_min_positive_similarity
        ),
        "reranker_enabled": settings.reranker_enabled,
        "reranker_configured": bool(
            settings.reranker_enabled and settings.dashscope_api_key.strip()
        ),
        "lexical_fallback": "BM25_CANDIDATES_REQUIRE_CLARIFICATION",
    }


def retrieve_metrics(
    session: Session,
    request: MetricRetrieveRequest,
    request_id: str,
    trace_id: str,
) -> MetricRetrieveResponse:
    settings = get_settings()
    runtime_diagnostics = retrieval_runtime_diagnostics()
    min_positive_similarity = (
        settings.local_sentence_transformer_min_positive_similarity
        if settings.embedding_provider == "local_sentence_transformer"
        else settings.vector_min_positive_similarity
    )
    records = load_metric_records(session, request.biz_domain)
    decision_policy = session.get(SemanticScopePolicy, request.biz_domain)
    selection_margin = decision_policy.selection_margin if decision_policy else 0.08

    staged_production_query = (
        is_explicitly_staged_production_query(request.normalized_query)
        or matches_unpublished_metric_name(
            session, request.biz_domain, request.normalized_query
        )
    )
    if staged_production_query:
        return MetricRetrieveResponse(
            request_id=request_id,
            trace_id=trace_id,
            gate_status="REJECT",
            mentions=[],
            reason_codes=[
                "CAPABILITY_STAGED" if staged_production_query else "METRIC_OUT_OF_SCOPE"
            ],
            clarification_message="",
            time_resolution=build_time_resolution_hint(request),
            dsl_generation_constraints=build_dsl_generation_constraints(request),
            runtime_diagnostics=runtime_diagnostics,
        )

    inherited_record = validated_inherited_metric(request, records)
    if inherited_record is not None:
        query_mode = (
            "multi_fact"
            if len(
                expression_model_ids(
                    inherited_record.version.expression_json,
                    inherited_record.version.semantic_model_id,
                )
            ) > 1
            else "single_model"
        )
        candidate = MetricCandidate(
            metric_id=inherited_record.metric.id,
            metric_version=inherited_record.version.version,
            display_name=inherited_record.metric.name,
            metric_type=inherited_record.metric.metric_type,
            unit=inherited_record.metric.unit,
            business_definition=inherited_record.metric.description,
            query_mode=query_mode,
            probability=1.0,
            retrieval_sources=["validated_conversation_context"],
            authorized=True,
        )
        return MetricRetrieveResponse(
            request_id=request_id,
            trace_id=trace_id,
            gate_status="PASS",
            mentions=[
                MetricMentionDecision(
                    text=request.normalized_query,
                    selected_metric_id=candidate.metric_id,
                    selected_metric_version=candidate.metric_version,
                    probability=1.0,
                    candidates=[candidate],
                )
            ],
            reason_codes=["VALIDATED_CONVERSATION_CONTEXT"],
            clarification_message="",
            time_resolution=build_time_resolution_hint(request),
            dsl_generation_constraints=build_dsl_generation_constraints(request),
            runtime_diagnostics=runtime_diagnostics,
        )

    if (
        not request.preprocess.inherit_context
        and is_underspecified_metric_query(request.normalized_query)
    ):
        candidates = [
            MetricCandidate(
                metric_id=record.metric.id,
                metric_version=record.version.version,
                display_name=record.metric.name,
                metric_type=record.metric.metric_type,
                unit=record.metric.unit,
                business_definition=record.metric.description,
                query_mode=(
                    "multi_fact"
                    if len(
                        expression_model_ids(
                            record.version.expression_json,
                            record.version.semantic_model_id,
                        )
                    ) > 1
                    else "single_model"
                ),
                probability=0.5,
                retrieval_sources=["underspecified_query_fallback"],
                authorized=True,
            )
            for record in records[:5]
        ]
        return MetricRetrieveResponse(
            request_id=request_id,
            trace_id=trace_id,
            gate_status="CLARIFY",
            mentions=[
                MetricMentionDecision(
                    text=request.normalized_query,
                    selected_metric_id="",
                    selected_metric_version=None,
                    probability=0.5 if candidates else 0.0,
                    candidates=candidates,
                )
            ],
            reason_codes=["MISSING_METRIC"],
            clarification_message="你想查看哪个指标？请选择一个指标口径后继续。",
            time_resolution=build_time_resolution_hint(request),
            dsl_generation_constraints=build_dsl_generation_constraints(request),
            runtime_diagnostics=runtime_diagnostics,
        )

    mentions = infer_mentions(request, records)
    decisions: list[MetricMentionDecision] = []
    statuses: list[str] = []

    for mention in mentions:
        scored = []
        explicit_lengths = explicit_match_lengths(mention, records)
        longest_explicit = max(explicit_lengths.values(), default=0)
        search_documents = [metric_search_document(record) for record in records]
        bm25_scores = bm25_relevance_scores(mention, search_documents)
        for record in records:
            score, sources = score_term(mention, record)
            explicit_length = explicit_lengths.get(record.metric.id, 0)
            if explicit_length and explicit_length == longest_explicit:
                score = max(score, 0.995)
                sources = [*sources, "longest_explicit_match"]
            elif explicit_length:
                score = min(score, 0.88)
                sources = [*sources, "shorter_explicit_match"]
            if score >= 0.45:
                scored.append((score, sources, record))
        lexical_top = max((item[0] for item in scored), default=0.0)
        vector_used = False
        # Operator-authored scope and ambiguity boundaries are policy gates, not
        # retrieval fallbacks.  Evaluate them for every path so a strong lexical
        # or BM25 false-positive cannot bypass a policy published from the UI.
        vector_result = search_metric_vectors(session, mention, request.biz_domain)
        vector_scores = vector_result.scores
        top_vector_similarity = max(
            (item.positive_similarity for item in vector_scores.values()),
            default=0.0,
        )
        scope_rejected = is_vector_scope_rejected(
            top_vector_similarity,
            vector_result.scope_negative_similarity,
            vector_result.scope_negative_threshold,
            vector_result.scope_margin,
        )
        ambiguity_matched = is_vector_scope_rejected(
            top_vector_similarity,
            vector_result.ambiguity_similarity,
            vector_result.ambiguity_threshold,
            vector_result.ambiguity_margin,
        )
        specificity_matched = (
            vector_result.specificity_similarity >= vector_result.specificity_threshold
            and vector_result.specificity_similarity
            >= vector_result.ambiguity_similarity + vector_result.specificity_margin
        )
        if scope_rejected:
            scored = []
            vector_scores = {}
        if lexical_top < 0.70:
            if not scope_rejected and top_vector_similarity < min_positive_similarity:
                vector_scores = {}
            elif not scope_rejected:
                vector_used = bool(vector_scores)
            for record_index, record in enumerate(records):
                vector_score = vector_scores.get(record.metric.id)
                bm25_score = bm25_scores[record_index] if not scope_rejected else 0.0
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
                calibrated_bm25 = (
                    0.45 + bm25_score * (0.35 if vector_used else 0.23)
                    if bm25_score > 0
                    else 0.0
                )
                if vector_used and vector_score is not None:
                    # Once semantic retrieval clears its provider-specific quality
                    # gate, preserve its ordering. BM25 is supporting evidence, not
                    # a 0.8-capped override that can erase the semantic margin.
                    combined = (
                        calibrated_vector * 0.75
                        + calibrated_bm25 * 0.20
                        + lexical_score * 0.05
                    )
                else:
                    combined = max(lexical_score, calibrated_bm25)
                sources = list(existing[1]) if existing else []
                if vector_score is not None:
                    sources.append("embedding")
                if bm25_score > 0:
                    sources.append("bm25" if vector_used else "bm25_clarify_fallback")
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
                query_mode=(
                    "multi_fact"
                    if len(
                        expression_model_ids(
                            record.version.expression_json,
                            record.version.semantic_model_id,
                        )
                    ) > 1
                    else "single_model"
                ),
                probability=score,
                retrieval_sources=sources,
                authorized=True,
            )
            for score, sources, record in scored
        ]

        if not candidates:
            # In a known business domain, an unmatched request is incomplete by
            # default.  Only the operator-managed out-of-scope boundary may turn
            # it into a rejection; this keeps the distinction UI-governable.
            status = "REJECT" if scope_rejected else "CLARIFY"
            selected_id = ""
            selected_version = None
            probability = 0.0
        else:
            top = candidates[0]
            margin = top.probability - (candidates[1].probability if len(candidates) > 1 else 0)
            governed_example_match = (
                "positive_example" in top.retrieval_sources
                and top.probability >= 0.86
            )
            if ambiguity_matched and not governed_example_match and not specificity_matched:
                status = "CLARIFY"
                selected_id = ""
                selected_version = None
            elif len(candidates) > 1 and margin < selection_margin and not governed_example_match:
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
        runtime_diagnostics=runtime_diagnostics,
    )
