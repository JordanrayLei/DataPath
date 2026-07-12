from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    BusinessDomain,
    Dimension,
    Metric,
    MetricAlias,
    MetricDimension,
    MetricDraft,
    MetricSemanticProfile,
    MetricVersion,
    SemanticModel,
)
from app.schemas.chatbi import (
    MetricDraftItem,
    MetricDraftListResponse,
    MetricDraftResponse,
    MetricDraftUpsertRequest,
    MetricManagementOption,
    MetricManagementOptionsResponse,
    MetricPublishResponse,
)
from app.services.metric_catalog import formula_text
from app.services.query_compiler import ALLOWED_FIELDS, CompilationError, compile_metric_expression


class MetricManagementError(ValueError):
    pass


def require_demo_workspace(workspace_id: str) -> None:
    if workspace_id != get_settings().default_workspace_id:
        raise MetricManagementError("workspace is not allowed")


def validate_definition(
    session: Session, payload: MetricDraftUpsertRequest
) -> dict[str, Any]:
    model = session.get(SemanticModel, payload.semantic_model_id)
    if model is None or model.status != "ACTIVE":
        raise MetricManagementError("semantic model does not exist or is inactive")
    if model.business_domain_id != payload.business_domain_id:
        raise MetricManagementError("semantic model does not belong to business domain")

    dimensions = session.scalars(
        select(Dimension).where(Dimension.id.in_(payload.dimension_ids))
    ).all()
    if len(dimensions) != len(set(payload.dimension_ids)):
        raise MetricManagementError("one or more dimensions do not exist")
    invalid_dimensions = [
        item.id
        for item in dimensions
        if item.status != "ACTIVE" or payload.semantic_model_id not in (item.mapping_json or {})
    ]
    if invalid_dimensions:
        raise MetricManagementError(
            f"dimensions are not mapped to semantic model: {', '.join(sorted(invalid_dimensions))}"
        )
    if payload.time_dimension_id not in payload.dimension_ids:
        raise MetricManagementError("time dimension must be included in available dimensions")
    time_dimension = next(
        (item for item in dimensions if item.id == payload.time_dimension_id), None
    )
    if time_dimension is None or time_dimension.dimension_type not in {"date", "time_grain"}:
        raise MetricManagementError("time dimension must be a date or time grain")

    expression_op = payload.expression.get("op")
    if payload.metric_type in {"ratio", "average"} and expression_op != "ratio":
        raise MetricManagementError("ratio or average metric must use a ratio expression")
    if payload.metric_type in {"amount", "count"} and expression_op == "ratio":
        raise MetricManagementError("ratio expression requires ratio or average metric type")

    lineage_fields: set[str] = set()
    try:
        compiled_expression = compile_metric_expression(
            payload.expression, payload.semantic_model_id, lineage_fields
        )
    except (CompilationError, KeyError, TypeError) as error:
        raise MetricManagementError(f"metric expression is invalid: {error}") from error

    return {
        "valid": True,
        "formula_text": formula_text(payload.expression),
        "compiled_expression": compiled_expression,
        "lineage_fields": sorted(lineage_fields),
        "warnings": [],
        "validated_at": datetime.now(UTC).isoformat(),
    }


def next_metric_version(session: Session, metric_id: str) -> int:
    current = session.scalar(
        select(func.max(MetricVersion.version)).where(MetricVersion.metric_id == metric_id)
    )
    return int(current or 0) + 1


def build_draft_item(session: Session, draft: MetricDraft) -> MetricDraftItem:
    metric = session.get(Metric, draft.metric_id)
    if metric is None:
        raise MetricManagementError("draft metric does not exist")
    return MetricDraftItem(
        draft_id=draft.draft_id,
        metric_id=draft.metric_id,
        business_domain_id=draft.business_domain_id,
        name=draft.name,
        description=draft.description,
        metric_type=draft.metric_type,
        unit=draft.unit,
        owner=draft.owner,
        metric_status=metric.status,
        next_version=next_metric_version(session, draft.metric_id),
        aliases=[str(item) for item in (draft.aliases_json or [])],
        positive_examples=[str(item) for item in (draft.positive_examples_json or [])],
        negative_examples=[str(item) for item in (draft.negative_examples_json or [])],
        semantic_model_id=draft.semantic_model_id,
        expression=draft.expression_json,
        formula_text=formula_text(draft.expression_json),
        default_aggregation=draft.default_aggregation,
        time_dimension_id=draft.time_dimension_id,
        dimension_ids=[str(item) for item in (draft.dimension_ids_json or [])],
        validation=draft.validation_json or {},
        updated_at=draft.updated_at,
    )


def management_options(
    session: Session, request_id: str, trace_id: str, workspace_id: str
) -> MetricManagementOptionsResponse:
    require_demo_workspace(workspace_id)
    domains = session.scalars(
        select(BusinessDomain).where(BusinessDomain.status == "ACTIVE").order_by(BusinessDomain.id.desc())
    ).all()
    models = session.scalars(
        select(SemanticModel).where(SemanticModel.status == "ACTIVE").order_by(SemanticModel.id.desc())
    ).all()
    dimensions = session.scalars(
        select(Dimension).where(Dimension.status == "ACTIVE").order_by(Dimension.id)
    ).all()
    return MetricManagementOptionsResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        domains=[
            MetricManagementOption(id=item.id, name=item.name, business_domain_id=item.id)
            for item in domains
        ],
        semantic_models=[
            MetricManagementOption(
                id=item.id,
                name=item.name,
                business_domain_id=item.business_domain_id,
                physical_table=item.physical_table,
                fields=sorted(ALLOWED_FIELDS.get(item.id, set())),
            )
            for item in models
        ],
        dimensions=[
            MetricManagementOption(
                id=item.id,
                name=item.name,
                fields=sorted((item.mapping_json or {}).keys()),
            )
            for item in dimensions
        ],
    )


def save_metric_draft(
    session: Session,
    payload: MetricDraftUpsertRequest,
    request_id: str,
    trace_id: str,
) -> MetricDraftResponse:
    require_demo_workspace(payload.workspace_id)
    validation = validate_definition(session, payload)
    metric = session.get(Metric, payload.metric_id)
    if metric is None:
        metric = Metric(
            id=payload.metric_id,
            business_domain_id=payload.business_domain_id,
            name=payload.name,
            description=payload.description,
            metric_type=payload.metric_type,
            unit=payload.unit,
            owner=payload.owner,
            status="DRAFT",
        )
        session.add(metric)
        session.flush()
    elif metric.business_domain_id != payload.business_domain_id:
        raise MetricManagementError("published metric cannot move to another business domain")

    draft = session.scalar(
        select(MetricDraft).where(MetricDraft.metric_id == payload.metric_id)
    )
    values = {
        "business_domain_id": payload.business_domain_id,
        "name": payload.name,
        "description": payload.description,
        "metric_type": payload.metric_type,
        "unit": payload.unit,
        "owner": payload.owner,
        "semantic_model_id": payload.semantic_model_id,
        "expression_json": payload.expression,
        "default_aggregation": payload.default_aggregation,
        "time_dimension_id": payload.time_dimension_id,
        "aliases_json": payload.aliases,
        "positive_examples_json": payload.positive_examples,
        "negative_examples_json": payload.negative_examples,
        "dimension_ids_json": payload.dimension_ids,
        "validation_json": validation,
        "created_by": get_settings().default_operator_id,
        "updated_at": datetime.now(UTC),
    }
    if draft is None:
        draft = MetricDraft(
            draft_id=f"md_{uuid.uuid4().hex}",
            metric_id=payload.metric_id,
            **values,
        )
        session.add(draft)
    else:
        for key, value in values.items():
            setattr(draft, key, value)
    session.commit()
    session.refresh(draft)
    return MetricDraftResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="DRAFT",
        draft=build_draft_item(session, draft),
    )


def list_metric_drafts(
    session: Session, request_id: str, trace_id: str, workspace_id: str
) -> MetricDraftListResponse:
    require_demo_workspace(workspace_id)
    drafts = session.scalars(select(MetricDraft).order_by(MetricDraft.updated_at.desc())).all()
    return MetricDraftListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        items=[build_draft_item(session, item) for item in drafts],
        total=len(drafts),
    )


def publish_metric_draft(
    session: Session,
    metric_id: str,
    request_id: str,
    trace_id: str,
    workspace_id: str,
) -> MetricPublishResponse:
    require_demo_workspace(workspace_id)
    draft = session.scalar(
        select(MetricDraft).where(MetricDraft.metric_id == metric_id).with_for_update()
    )
    if draft is None:
        raise MetricManagementError("metric draft does not exist")
    metric = session.get(Metric, metric_id)
    if metric is None:
        raise MetricManagementError("metric does not exist")

    payload = MetricDraftUpsertRequest(
        workspace_id=workspace_id,
        metric_id=draft.metric_id,
        business_domain_id=draft.business_domain_id,
        name=draft.name,
        description=draft.description,
        metric_type=draft.metric_type,
        unit=draft.unit,
        owner=draft.owner,
        aliases=draft.aliases_json,
        positive_examples=draft.positive_examples_json,
        negative_examples=draft.negative_examples_json,
        semantic_model_id=draft.semantic_model_id,
        expression=draft.expression_json,
        default_aggregation=draft.default_aggregation,
        time_dimension_id=draft.time_dimension_id,
        dimension_ids=draft.dimension_ids_json,
    )
    validate_definition(session, payload)
    version_number = next_metric_version(session, metric_id)
    published_at = datetime.now(UTC)

    metric.business_domain_id = draft.business_domain_id
    metric.name = draft.name
    metric.description = draft.description
    metric.metric_type = draft.metric_type
    metric.unit = draft.unit
    metric.owner = draft.owner
    metric.status = "PUBLISHED"

    session.add(
        MetricVersion(
            metric_id=metric_id,
            version=version_number,
            semantic_model_id=draft.semantic_model_id,
            expression_json=draft.expression_json,
            default_aggregation=draft.default_aggregation,
            time_dimension_id=draft.time_dimension_id,
            status="PUBLISHED",
            published_at=published_at,
        )
    )
    session.execute(delete(MetricAlias).where(MetricAlias.metric_id == metric_id))
    session.execute(delete(MetricDimension).where(MetricDimension.metric_id == metric_id))
    session.add_all(
        [MetricAlias(metric_id=metric_id, alias=item) for item in draft.aliases_json]
    )
    profile = session.get(MetricSemanticProfile, metric_id)
    profile_values = {
        "positive_examples_json": draft.positive_examples_json,
        "negative_examples_json": draft.negative_examples_json,
        "retrieval_config_json": {"enabled": True},
        "updated_by": get_settings().default_operator_id,
        "updated_at": published_at,
    }
    if profile is None:
        session.add(MetricSemanticProfile(metric_id=metric_id, **profile_values))
    else:
        for key, value in profile_values.items():
            setattr(profile, key, value)
    session.add_all(
        [
            MetricDimension(metric_id=metric_id, dimension_id=item)
            for item in draft.dimension_ids_json
        ]
    )
    session.delete(draft)
    session.commit()
    return MetricPublishResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="PUBLISHED",
        metric_id=metric_id,
        version=version_number,
        published_at=published_at,
    )
