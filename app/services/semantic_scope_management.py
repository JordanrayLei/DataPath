from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import BusinessDomain, SemanticScopeExample, SemanticScopePolicy
from app.schemas.chatbi import (
    SemanticScopeExampleInput,
    SemanticScopeExampleItem,
    SemanticScopeExampleListResponse,
    SemanticScopeExampleReplaceRequest,
    SemanticScopePreviewItem,
    SemanticScopePreviewRequest,
    SemanticScopePreviewResponse,
    SemanticAmbiguityPolicyRequest,
    SemanticAmbiguityPolicyResponse,
)
from app.services.embedding_provider import EmbeddingProviderError, get_embedding_provider
from app.services.metric_retrieval import is_vector_scope_rejected
from app.services.metric_vector_index import normalize_vector_query, search_metric_vectors


class SemanticScopeManagementError(ValueError):
    pass


def _embed_in_batches(texts: list[str]) -> tuple[list[list[float]], int, int]:
    settings = get_settings()
    vectors: list[list[float]] = []
    total_tokens = 0
    dimensions = settings.embedding_dimensions
    provider = get_embedding_provider()
    for offset in range(0, len(texts), settings.embedding_batch_size):
        batch = provider.embed(texts[offset : offset + settings.embedding_batch_size])
        vectors.extend(batch.vectors)
        total_tokens += batch.total_tokens
        dimensions = batch.dimensions
    return vectors, total_tokens, dimensions


def _require_workspace(workspace_id: str) -> None:
    if workspace_id != get_settings().default_workspace_id:
        raise SemanticScopeManagementError("workspace is not allowed")


def _require_domain(session: Session, business_domain_id: str) -> None:
    domain = session.get(BusinessDomain, business_domain_id)
    if domain is None or domain.status != "ACTIVE":
        raise SemanticScopeManagementError("business domain does not exist or is inactive")


def normalize_scope_examples(
    examples: list[SemanticScopeExampleInput],
) -> list[SemanticScopeExampleInput]:
    normalized: list[SemanticScopeExampleInput] = []
    seen: set[str] = set()
    for item in examples:
        text = " ".join(item.text.split()).strip(" ，,。")
        reason = " ".join(item.reason.split())
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        normalized.append(SemanticScopeExampleInput(text=text, reason=reason))
    if len(normalized) < 3:
        raise SemanticScopeManagementError("at least three unique scope examples are required")
    return normalized


def _item(row: SemanticScopeExample) -> SemanticScopeExampleItem:
    return SemanticScopeExampleItem(
        id=row.id,
        business_domain_id=row.business_domain_id,
        text=row.text,
        label=row.label,
        reason=row.reason,
        is_active=row.is_active,
        embedding_model=row.embedding_model,
        created_at=row.created_at,
    )


def list_scope_examples(
    session: Session,
    business_domain_id: str,
    workspace_id: str,
    request_id: str,
    trace_id: str,
) -> SemanticScopeExampleListResponse:
    _require_workspace(workspace_id)
    _require_domain(session, business_domain_id)
    rows = session.scalars(
        select(SemanticScopeExample)
        .where(
            SemanticScopeExample.business_domain_id == business_domain_id,
            SemanticScopeExample.label == "OUT_OF_SCOPE",
            SemanticScopeExample.is_active.is_(True),
        )
        .order_by(SemanticScopeExample.id)
    ).all()
    settings = get_settings()
    policy = session.get(SemanticScopePolicy, business_domain_id)
    return SemanticScopeExampleListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        business_domain_id=business_domain_id,
        items=[_item(row) for row in rows],
        total=len(rows),
        embedding_model=settings.embedding_model,
        negative_threshold=(policy.negative_threshold if policy else settings.vector_scope_negative_threshold),
        margin=(policy.margin if policy else settings.vector_scope_margin),
    )


def replace_scope_examples(
    session: Session,
    business_domain_id: str,
    payload: SemanticScopeExampleReplaceRequest,
    request_id: str,
    trace_id: str,
) -> SemanticScopeExampleListResponse:
    _require_workspace(payload.workspace_id)
    _require_domain(session, business_domain_id)
    examples = normalize_scope_examples(payload.examples)
    settings = get_settings()
    vectors: list[list[float]] = []
    total_tokens = 0
    dimensions = settings.embedding_dimensions
    try:
        vectors, total_tokens, dimensions = _embed_in_batches(
            [item.text for item in examples]
        )
    except (EmbeddingProviderError, RuntimeError) as error:
        raise SemanticScopeManagementError(f"scope embedding failed: {error}") from error
    if len(vectors) != len(examples):
        raise SemanticScopeManagementError("scope embedding result count is invalid")

    session.execute(
        delete(SemanticScopeExample).where(
            SemanticScopeExample.business_domain_id == business_domain_id,
            SemanticScopeExample.label == "OUT_OF_SCOPE",
        )
    )
    policy = session.get(SemanticScopePolicy, business_domain_id)
    if policy is None:
        policy = SemanticScopePolicy(
            business_domain_id=business_domain_id,
            negative_threshold=payload.negative_threshold,
            margin=payload.margin,
            updated_by=settings.default_operator_id,
        )
        session.add(policy)
    else:
        policy.negative_threshold = payload.negative_threshold
        policy.margin = payload.margin
        policy.updated_by = settings.default_operator_id
        policy.updated_at = datetime.now(UTC)
    rows = []
    for item, vector in zip(examples, vectors, strict=True):
        row = SemanticScopeExample(
            business_domain_id=business_domain_id,
            text=item.text,
            label="OUT_OF_SCOPE",
            reason=item.reason,
            source_hash=hashlib.sha256(item.text.casefold().encode("utf-8")).hexdigest(),
            embedding_model=settings.embedding_model,
            embedding_dimensions=dimensions,
            embedding=vector,
            is_active=True,
        )
        session.add(row)
        rows.append(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return SemanticScopeExampleListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        business_domain_id=business_domain_id,
        items=[_item(row) for row in rows],
        total=len(rows),
        embedding_model=settings.embedding_model,
        total_tokens=total_tokens,
        negative_threshold=payload.negative_threshold,
        margin=payload.margin,
    )


def preview_scope_examples(
    session: Session,
    business_domain_id: str,
    payload: SemanticScopePreviewRequest,
    request_id: str,
    trace_id: str,
) -> SemanticScopePreviewResponse:
    _require_workspace(payload.workspace_id)
    _require_domain(session, business_domain_id)
    examples = normalize_scope_examples(payload.examples)
    queries = [" ".join(item.split()).strip() for item in payload.queries if item.strip()]
    if not queries:
        raise SemanticScopeManagementError("at least one preview query is required")
    settings = get_settings()
    query_texts = [normalize_vector_query(item) for item in queries]
    if settings.embedding_provider == "local_sentence_transformer":
        query_texts = [
            f"{settings.local_sentence_transformer_query_instruction}{item}"
            for item in query_texts
        ]
    try:
        scope_vectors, _, _ = _embed_in_batches([item.text for item in examples])
        query_vectors, _, _ = _embed_in_batches(query_texts)
    except (EmbeddingProviderError, RuntimeError) as error:
        raise SemanticScopeManagementError(f"scope preview embedding failed: {error}") from error

    items: list[SemanticScopePreviewItem] = []
    for query, query_vector in zip(queries, query_vectors, strict=True):
        similarities = [
            sum(left * right for left, right in zip(query_vector, scope_vector, strict=True))
            for scope_vector in scope_vectors
        ]
        best_index = max(range(len(similarities)), key=similarities.__getitem__)
        scope_similarity = max(0.0, min(1.0, similarities[best_index]))
        vector_result = search_metric_vectors(session, query, business_domain_id)
        top_metric_similarity = max(
            (item.positive_similarity for item in vector_result.scores.values()),
            default=0.0,
        )
        rejected = is_vector_scope_rejected(
            top_metric_similarity,
            scope_similarity,
            payload.negative_threshold,
            payload.margin,
        )
        items.append(
            SemanticScopePreviewItem(
                query=query,
                top_metric_similarity=round(top_metric_similarity, 4),
                scope_similarity=round(scope_similarity, 4),
                nearest_scope_example=examples[best_index].text,
                predicted_status="REJECT" if rejected else "KEEP",
            )
        )
    return SemanticScopePreviewResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        business_domain_id=business_domain_id,
        negative_threshold=payload.negative_threshold,
        margin=payload.margin,
        items=items,
        reject_count=sum(item.predicted_status == "REJECT" for item in items),
        keep_count=sum(item.predicted_status == "KEEP" for item in items),
    )


def list_ambiguity_policy(
    session: Session,
    business_domain_id: str,
    workspace_id: str,
    request_id: str,
    trace_id: str,
) -> SemanticAmbiguityPolicyResponse:
    _require_workspace(workspace_id)
    _require_domain(session, business_domain_id)
    rows = session.scalars(
        select(SemanticScopeExample)
        .where(
            SemanticScopeExample.business_domain_id == business_domain_id,
            SemanticScopeExample.label == "AMBIGUOUS",
            SemanticScopeExample.is_active.is_(True),
        )
        .order_by(SemanticScopeExample.id)
    ).all()
    specificity_rows = session.scalars(
        select(SemanticScopeExample)
        .where(
            SemanticScopeExample.business_domain_id == business_domain_id,
            SemanticScopeExample.label == "SPECIFIC",
            SemanticScopeExample.is_active.is_(True),
        )
        .order_by(SemanticScopeExample.id)
    ).all()
    policy = session.get(SemanticScopePolicy, business_domain_id)
    return SemanticAmbiguityPolicyResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        business_domain_id=business_domain_id,
        items=[_item(row) for row in rows],
        total=len(rows),
        specificity_items=[_item(row) for row in specificity_rows],
        specificity_total=len(specificity_rows),
        embedding_model=get_settings().embedding_model,
        selection_margin=policy.selection_margin if policy else 0.08,
        ambiguity_threshold=policy.ambiguity_threshold if policy else 0.64,
        ambiguity_margin=policy.ambiguity_margin if policy else 0.06,
        specificity_threshold=policy.specificity_threshold if policy else 0.60,
        specificity_margin=policy.specificity_margin if policy else 0.02,
    )


def replace_ambiguity_policy(
    session: Session,
    business_domain_id: str,
    payload: SemanticAmbiguityPolicyRequest,
    request_id: str,
    trace_id: str,
) -> SemanticAmbiguityPolicyResponse:
    _require_workspace(payload.workspace_id)
    _require_domain(session, business_domain_id)
    examples = normalize_scope_examples(payload.examples)
    specificity_examples = (
        normalize_scope_examples(payload.specificity_examples)
        if payload.specificity_examples
        else []
    )
    settings = get_settings()
    try:
        vectors, total_tokens, dimensions = _embed_in_batches([item.text for item in examples])
        specificity_vectors = []
        if specificity_examples:
            specificity_vectors, specificity_tokens, specificity_dimensions = _embed_in_batches(
                [item.text for item in specificity_examples]
            )
            total_tokens += specificity_tokens
            if specificity_dimensions != dimensions:
                raise SemanticScopeManagementError("specificity embedding dimensions do not match")
    except (EmbeddingProviderError, RuntimeError) as error:
        raise SemanticScopeManagementError(f"ambiguity embedding failed: {error}") from error
    session.execute(
        delete(SemanticScopeExample).where(
            SemanticScopeExample.business_domain_id == business_domain_id,
            SemanticScopeExample.label == "AMBIGUOUS",
        )
    )
    if specificity_examples:
        session.execute(
            delete(SemanticScopeExample).where(
                SemanticScopeExample.business_domain_id == business_domain_id,
                SemanticScopeExample.label == "SPECIFIC",
            )
        )
    policy = session.get(SemanticScopePolicy, business_domain_id)
    if policy is None:
        policy = SemanticScopePolicy(
            business_domain_id=business_domain_id,
            negative_threshold=settings.vector_scope_negative_threshold,
            margin=settings.vector_scope_margin,
            updated_by=settings.default_operator_id,
        )
        session.add(policy)
    policy.selection_margin = payload.selection_margin
    policy.ambiguity_threshold = payload.ambiguity_threshold
    policy.ambiguity_margin = payload.ambiguity_margin
    policy.specificity_threshold = payload.specificity_threshold
    policy.specificity_margin = payload.specificity_margin
    policy.updated_by = settings.default_operator_id
    policy.updated_at = datetime.now(UTC)
    rows = []
    for item, vector in zip(examples, vectors, strict=True):
        row = SemanticScopeExample(
            business_domain_id=business_domain_id,
            text=item.text,
            label="AMBIGUOUS",
            reason=item.reason,
            source_hash=hashlib.sha256(item.text.casefold().encode("utf-8")).hexdigest(),
            embedding_model=settings.embedding_model,
            embedding_dimensions=dimensions,
            embedding=vector,
            is_active=True,
        )
        session.add(row)
        rows.append(row)
    if specificity_examples:
        specificity_rows = []
        for item, vector in zip(specificity_examples, specificity_vectors, strict=True):
            row = SemanticScopeExample(
                business_domain_id=business_domain_id,
                text=item.text,
                label="SPECIFIC",
                reason=item.reason,
                source_hash=hashlib.sha256(item.text.casefold().encode("utf-8")).hexdigest(),
                embedding_model=settings.embedding_model,
                embedding_dimensions=dimensions,
                embedding=vector,
                is_active=True,
            )
            session.add(row)
            specificity_rows.append(row)
    else:
        specificity_rows = session.scalars(
            select(SemanticScopeExample)
            .where(
                SemanticScopeExample.business_domain_id == business_domain_id,
                SemanticScopeExample.label == "SPECIFIC",
                SemanticScopeExample.is_active.is_(True),
            )
            .order_by(SemanticScopeExample.id)
        ).all()
    session.commit()
    for row in rows:
        session.refresh(row)
    for row in specificity_rows:
        session.refresh(row)
    return SemanticAmbiguityPolicyResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        business_domain_id=business_domain_id,
        items=[_item(row) for row in rows],
        total=len(rows),
        specificity_items=[_item(row) for row in specificity_rows],
        specificity_total=len(specificity_rows),
        embedding_model=settings.embedding_model,
        total_tokens=total_tokens,
        selection_margin=payload.selection_margin,
        ambiguity_threshold=payload.ambiguity_threshold,
        ambiguity_margin=payload.ambiguity_margin,
        specificity_threshold=payload.specificity_threshold,
        specificity_margin=payload.specificity_margin,
    )
