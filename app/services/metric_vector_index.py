from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import Metric, MetricEmbedding, SemanticScopeExample, SemanticScopePolicy
from app.services.embedding_provider import EmbeddingProviderError, get_embedding_provider


@dataclass(frozen=True)
class MetricVectorScore:
    metric_id: str
    positive_similarity: float
    negative_similarity: float
    source_text: str


@dataclass(frozen=True)
class MetricVectorSearchResult:
    scores: dict[str, MetricVectorScore]
    scope_negative_similarity: float = 0.0
    scope_negative_text: str = ""
    scope_negative_threshold: float = 0.64
    scope_margin: float = 0.06
    ambiguity_similarity: float = 0.0
    ambiguity_text: str = ""
    ambiguity_threshold: float = 0.64
    ambiguity_margin: float = 0.06
    specificity_similarity: float = 0.0
    specificity_text: str = ""
    specificity_threshold: float = 0.60
    specificity_margin: float = 0.02


def source_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def normalize_vector_query(text: str) -> str:
    """Remove presentation and time syntax that should not define metric identity."""

    normalized = text.casefold().strip()
    normalized = re.sub(
        r"(?:请|麻烦|帮我)?(?:查看|查询|统计|分析|计算|展示|看一下)",
        " ",
        normalized,
    )
    normalized = re.sub(r"\b(?:19|20)\d{2}年", " ", normalized)
    normalized = re.sub(r"\b(?:19|20)\d{2}[-/.]\d{1,2}(?:[-/.]\d{1,2})?", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" ，,。.!！?？")
    return normalized or text.strip()


def metric_documents(metric: Metric) -> list[tuple[str, str]]:
    documents = [("name", metric.name), ("description", metric.description)]
    documents.extend(("alias", item.alias) for item in metric.aliases)
    profile = metric.semantic_profile
    if profile:
        documents.extend(("positive_example", str(item)) for item in profile.positive_examples_json or [])
        documents.extend(("negative_example", str(item)) for item in profile.negative_examples_json or [])
    seen: set[tuple[str, str]] = set()
    return [item for item in documents if item[1].strip() and not (item in seen or seen.add(item))]


def rebuild_metric_vector_index(session: Session) -> dict[str, int]:
    settings = get_settings()
    metrics = session.scalars(
        select(Metric)
        .options(selectinload(Metric.aliases), selectinload(Metric.semantic_profile))
        .where(Metric.status == "PUBLISHED")
        .order_by(Metric.id)
    ).all()
    sources = [
        (metric.id, source_type, text)
        for metric in metrics
        for source_type, text in metric_documents(metric)
    ]
    session.execute(
        delete(MetricEmbedding).where(MetricEmbedding.embedding_model == settings.embedding_model)
    )
    session.flush()

    total_tokens = 0
    for offset in range(0, len(sources), settings.embedding_batch_size):
        batch = sources[offset : offset + settings.embedding_batch_size]
        result = get_embedding_provider().embed([item[2] for item in batch])
        total_tokens += result.total_tokens
        for (metric_id, source_type, text), vector in zip(batch, result.vectors, strict=True):
            session.add(
                MetricEmbedding(
                    metric_id=metric_id,
                    source_type=source_type,
                    source_text=text,
                    source_hash=source_hash(text),
                    embedding_model=settings.embedding_model,
                    embedding_dimensions=result.dimensions,
                    embedding=vector,
                    is_active=True,
                )
            )
    session.commit()
    scope_examples = session.scalars(
        select(SemanticScopeExample).where(SemanticScopeExample.is_active.is_(True))
    ).all()
    for offset in range(0, len(scope_examples), settings.embedding_batch_size):
        batch = scope_examples[offset : offset + settings.embedding_batch_size]
        result = get_embedding_provider().embed([item.text for item in batch])
        total_tokens += result.total_tokens
        for item, vector in zip(batch, result.vectors, strict=True):
            item.embedding_model = settings.embedding_model
            item.embedding_dimensions = result.dimensions
            item.embedding = vector
    session.commit()
    return {
        "metrics": len(metrics),
        "documents": len(sources),
        "scope_examples": len(scope_examples),
        "total_tokens": total_tokens,
    }


def refresh_metric_vector_index(session: Session, metric_id: str) -> dict[str, int | str]:
    """Atomically refresh one published metric after a governed frontend release."""

    settings = get_settings()
    metric = session.scalar(
        select(Metric)
        .options(selectinload(Metric.aliases), selectinload(Metric.semantic_profile))
        .where(Metric.id == metric_id, Metric.status == "PUBLISHED")
    )
    if metric is None:
        raise ValueError("published metric does not exist")
    sources = metric_documents(metric)
    embedded: list[tuple[str, str, list[float]]] = []
    total_tokens = 0
    for offset in range(0, len(sources), settings.embedding_batch_size):
        batch = sources[offset : offset + settings.embedding_batch_size]
        result = get_embedding_provider().embed([item[1] for item in batch])
        total_tokens += result.total_tokens
        embedded.extend(
            (source_type, source_text, vector)
            for (source_type, source_text), vector in zip(batch, result.vectors, strict=True)
        )
    session.execute(
        delete(MetricEmbedding).where(
            MetricEmbedding.metric_id == metric_id,
            MetricEmbedding.embedding_model == settings.embedding_model,
        )
    )
    session.add_all(
        [
            MetricEmbedding(
                metric_id=metric_id,
                source_type=source_type,
                source_text=source_text,
                source_hash=source_hash(source_text),
                embedding_model=settings.embedding_model,
                embedding_dimensions=settings.embedding_dimensions,
                embedding=vector,
                is_active=True,
            )
            for source_type, source_text, vector in embedded
        ]
    )
    session.commit()
    return {
        "metric_id": metric_id,
        "documents": len(embedded),
        "total_tokens": total_tokens,
        "embedding_model": settings.embedding_model,
    }


def search_metric_vectors(
    session: Session,
    query: str,
    business_domain_id: str,
) -> MetricVectorSearchResult:
    settings = get_settings()
    policy = session.get(SemanticScopePolicy, business_domain_id)
    scope_negative_threshold = (
        policy.negative_threshold if policy else settings.vector_scope_negative_threshold
    )
    scope_margin = policy.margin if policy else settings.vector_scope_margin
    ambiguity_threshold = policy.ambiguity_threshold if policy else 0.64
    ambiguity_margin = policy.ambiguity_margin if policy else 0.06
    specificity_threshold = policy.specificity_threshold if policy else 0.60
    specificity_margin = policy.specificity_margin if policy else 0.02
    query_text = normalize_vector_query(query)
    if settings.embedding_provider == "local_sentence_transformer":
        query_text = f"{settings.local_sentence_transformer_query_instruction}{query_text}"
    try:
        query_vector = get_embedding_provider().embed([query_text]).vectors[0]
    except (EmbeddingProviderError, IndexError):
        return MetricVectorSearchResult(
            scores={},
            scope_negative_threshold=scope_negative_threshold,
            scope_margin=scope_margin,
            ambiguity_threshold=ambiguity_threshold,
            ambiguity_margin=ambiguity_margin,
            specificity_threshold=specificity_threshold,
            specificity_margin=specificity_margin,
        )

    distance = MetricEmbedding.embedding.cosine_distance(query_vector)
    rows = session.execute(
        select(MetricEmbedding, distance.label("distance"))
        .join(Metric, Metric.id == MetricEmbedding.metric_id)
        .where(
            MetricEmbedding.embedding_model == settings.embedding_model,
            MetricEmbedding.is_active.is_(True),
            Metric.business_domain_id == business_domain_id,
            Metric.status == "PUBLISHED",
        )
        .order_by(distance)
        .limit(max(settings.vector_search_limit * 40, 200))
    ).all()

    aggregated: dict[str, dict[str, object]] = {}
    for row, value in rows:
        similarity = max(0.0, min(1.0, 1.0 - float(value)))
        current = aggregated.setdefault(
            row.metric_id,
            {"positive": 0.0, "negative": 0.0, "source_text": ""},
        )
        key = "negative" if row.source_type == "negative_example" else "positive"
        if similarity > float(current[key]):
            current[key] = similarity
            if key == "positive":
                current["source_text"] = row.source_text

    scores = {
        metric_id: MetricVectorScore(
            metric_id=metric_id,
            positive_similarity=float(values["positive"]),
            negative_similarity=float(values["negative"]),
            source_text=str(values["source_text"]),
        )
        for metric_id, values in aggregated.items()
        if float(values["positive"]) >= settings.vector_similarity_threshold
    }
    example_distance = SemanticScopeExample.embedding.cosine_distance(query_vector)
    boundary_rows = session.execute(
        select(SemanticScopeExample, example_distance.label("distance"))
        .where(
            SemanticScopeExample.business_domain_id == business_domain_id,
            SemanticScopeExample.label.in_(("OUT_OF_SCOPE", "AMBIGUOUS", "SPECIFIC")),
            SemanticScopeExample.embedding_model == settings.embedding_model,
            SemanticScopeExample.is_active.is_(True),
        )
        .order_by(example_distance)
        .limit(200)
    ).all()
    if not boundary_rows:
        return MetricVectorSearchResult(
            scores=scores,
            scope_negative_threshold=scope_negative_threshold,
            scope_margin=scope_margin,
            ambiguity_threshold=ambiguity_threshold,
            ambiguity_margin=ambiguity_margin,
            specificity_threshold=specificity_threshold,
            specificity_margin=specificity_margin,
        )
    by_label = {}
    for example, value in boundary_rows:
        by_label.setdefault(example.label, (example, value))
    scope_example, scope_value = by_label.get("OUT_OF_SCOPE", (None, 1.0))
    ambiguity_example, ambiguity_value = by_label.get("AMBIGUOUS", (None, 1.0))
    specificity_example, specificity_value = by_label.get("SPECIFIC", (None, 1.0))
    return MetricVectorSearchResult(
        scores=scores,
        scope_negative_similarity=max(0.0, min(1.0, 1.0 - float(scope_value))) if scope_example else 0.0,
        scope_negative_text=scope_example.text if scope_example else "",
        scope_negative_threshold=scope_negative_threshold,
        scope_margin=scope_margin,
        ambiguity_similarity=max(0.0, min(1.0, 1.0 - float(ambiguity_value))) if ambiguity_example else 0.0,
        ambiguity_text=ambiguity_example.text if ambiguity_example else "",
        ambiguity_threshold=ambiguity_threshold,
        ambiguity_margin=ambiguity_margin,
        specificity_similarity=max(0.0, min(1.0, 1.0 - float(specificity_value))) if specificity_example else 0.0,
        specificity_text=specificity_example.text if specificity_example else "",
        specificity_threshold=specificity_threshold,
        specificity_margin=specificity_margin,
    )
