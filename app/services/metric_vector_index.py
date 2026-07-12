from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import Metric, MetricEmbedding, SemanticScopeExample
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


def source_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


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


def search_metric_vectors(
    session: Session,
    query: str,
    business_domain_id: str,
) -> MetricVectorSearchResult:
    settings = get_settings()
    try:
        query_vector = get_embedding_provider().embed([query]).vectors[0]
    except (EmbeddingProviderError, IndexError):
        return MetricVectorSearchResult(scores={})

    distance = MetricEmbedding.embedding.cosine_distance(query_vector)
    rows = session.execute(
        select(MetricEmbedding, distance.label("distance"))
        .where(
            MetricEmbedding.embedding_model == settings.embedding_model,
            MetricEmbedding.is_active.is_(True),
        )
        .order_by(distance)
        .limit(max(settings.vector_search_limit * 6, 20))
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
    scope_distance = SemanticScopeExample.embedding.cosine_distance(query_vector)
    scope_row = session.execute(
        select(SemanticScopeExample, scope_distance.label("distance"))
        .where(
            SemanticScopeExample.business_domain_id == business_domain_id,
            SemanticScopeExample.label == "OUT_OF_SCOPE",
            SemanticScopeExample.embedding_model == settings.embedding_model,
            SemanticScopeExample.is_active.is_(True),
        )
        .order_by(scope_distance)
        .limit(1)
    ).first()
    if scope_row is None:
        return MetricVectorSearchResult(scores=scores)
    scope_example, scope_value = scope_row
    return MetricVectorSearchResult(
        scores=scores,
        scope_negative_similarity=max(0.0, min(1.0, 1.0 - float(scope_value))),
        scope_negative_text=scope_example.text,
    )
