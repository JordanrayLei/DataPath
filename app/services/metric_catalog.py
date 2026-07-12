from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import (
    BusinessDomain,
    Dimension,
    Metric,
    MetricAlias,
    MetricDimension,
    MetricSemanticProfile,
    MetricVersion,
    SemanticModel,
)
from app.schemas.chatbi import (
    MetricCatalogDetailResponse,
    MetricCatalogDimension,
    MetricCatalogItem,
    MetricCatalogListResponse,
    MetricCatalogSemanticModel,
    MetricCatalogVersion,
)


class MetricCatalogError(ValueError):
    pass


def extract_expression_fields(expression: Any) -> list[str]:
    fields: list[str] = []
    if isinstance(expression, dict):
        field = expression.get("field")
        if isinstance(field, str):
            fields.append(field)
        for value in expression.values():
            fields.extend(extract_expression_fields(value))
    elif isinstance(expression, list):
        for item in expression:
            fields.extend(extract_expression_fields(item))
    return list(dict.fromkeys(fields))


def formula_text(expression: dict[str, Any]) -> str:
    op = expression.get("op")
    if op == "sum":
        return f"SUM({expression.get('field')})"
    if op == "avg":
        return f"AVG({expression.get('field')})"
    if op == "count_distinct":
        return f"COUNT(DISTINCT {expression.get('field')})"
    if op == "count":
        return f"COUNT({expression.get('field', '*')})"
    if op == "ratio":
        numerator = formula_text(expression.get("numerator", {}))
        denominator = formula_text(expression.get("denominator", {}))
        scale = expression.get("scale", 1)
        suffix = f" * {scale}" if scale not in (None, 1) else ""
        return f"({numerator}) / NULLIF(({denominator}), 0){suffix}"
    return str(expression)


def example_questions(metric: Metric, dimensions: list[Dimension]) -> list[str]:
    questions = [f"最近一年每月 {metric.name} 趋势如何？"]
    dimension_ids = {dimension.id for dimension in dimensions}
    if "D_REGION" in dimension_ids:
        questions.append(f"各地区 {metric.name} 排名")
    if "D_AD_PLATFORM" in dimension_ids:
        questions.append(f"各广告平台 {metric.name} 表现如何？")
    questions.append(f"{metric.name} 最近表现怎么样？")
    return list(dict.fromkeys(questions))[:3]


def latest_published_version(session: Session, metric_id: str) -> MetricVersion | None:
    return session.scalar(
        select(MetricVersion)
        .where(
            MetricVersion.metric_id == metric_id,
            MetricVersion.status == "PUBLISHED",
        )
        .order_by(MetricVersion.version.desc())
        .limit(1)
    )


def metric_dimensions(session: Session, metric_id: str) -> list[Dimension]:
    return session.scalars(
        select(Dimension)
        .join(MetricDimension, MetricDimension.dimension_id == Dimension.id)
        .where(MetricDimension.metric_id == metric_id)
        .order_by(Dimension.id)
    ).all()


def metric_aliases(session: Session, metric_id: str) -> list[str]:
    return session.scalars(
        select(MetricAlias.alias)
        .where(MetricAlias.metric_id == metric_id)
        .order_by(MetricAlias.alias)
    ).all()


def build_metric_item(
    session: Session,
    metric: Metric,
    domain: BusinessDomain,
    version: MetricVersion,
    model: SemanticModel,
) -> MetricCatalogItem:
    dimensions = metric_dimensions(session, metric.id)
    aliases = metric_aliases(session, metric.id)
    profile = session.get(MetricSemanticProfile, metric.id)
    expression = version.expression_json or {}
    fields = extract_expression_fields(expression)
    return MetricCatalogItem(
        metric_id=metric.id,
        business_domain_id=metric.business_domain_id,
        business_domain_name=domain.name,
        name=metric.name,
        description=metric.description,
        metric_type=metric.metric_type,
        unit=metric.unit,
        owner=metric.owner,
        status=metric.status,
        latest_version=version.version,
        aliases=aliases,
        positive_examples=[str(item) for item in ((profile.positive_examples_json if profile else []) or [])],
        negative_examples=[str(item) for item in ((profile.negative_examples_json if profile else []) or [])],
        dimensions=[
            MetricCatalogDimension(
                dimension_id=dimension.id,
                name=dimension.name,
                dimension_type=dimension.dimension_type,
                allowed_operators=[str(item) for item in (dimension.allowed_operators or [])],
            )
            for dimension in dimensions
        ],
        semantic_model=MetricCatalogSemanticModel(
            semantic_model_id=model.id,
            name=model.name,
            warehouse=model.warehouse,
            physical_table=model.physical_table,
            default_time_field=model.default_time_field,
        ),
        formula_text=formula_text(expression),
        lineage={
            "models": [model.id],
            "tables": [model.physical_table],
            "fields": fields,
        },
        example_questions=(
            [str(item) for item in (profile.positive_examples_json or [])][:3]
            if profile and profile.positive_examples_json
            else example_questions(metric, dimensions)
        ),
    )


def load_metric_catalog_rows(
    session: Session,
    domain: str = "ALL",
    limit: int = 50,
) -> list[tuple[Metric, BusinessDomain, MetricVersion, SemanticModel]]:
    if limit < 1 or limit > 200:
        raise MetricCatalogError("limit must be between 1 and 200")
    if domain not in {"ALL", "sales", "advertising"}:
        raise MetricCatalogError("domain is invalid")

    filters = [
        Metric.status == "PUBLISHED",
        MetricVersion.status == "PUBLISHED",
    ]
    if domain != "ALL":
        filters.append(Metric.business_domain_id == domain)

    rows = session.execute(
        select(Metric, BusinessDomain, MetricVersion, SemanticModel)
        .join(BusinessDomain, BusinessDomain.id == Metric.business_domain_id)
        .join(MetricVersion, MetricVersion.metric_id == Metric.id)
        .join(SemanticModel, SemanticModel.id == MetricVersion.semantic_model_id)
        .where(*filters)
        .order_by(Metric.business_domain_id, Metric.id, MetricVersion.version.desc())
    ).all()

    latest: dict[str, tuple[Metric, BusinessDomain, MetricVersion, SemanticModel]] = {}
    for metric, business_domain, version, model in rows:
        latest.setdefault(metric.id, (metric, business_domain, version, model))
    return list(latest.values())[:limit]


def list_metric_catalog(
    session: Session,
    request_id: str,
    trace_id: str,
    workspace_id: str = "demo",
    domain: str = "ALL",
    limit: int = 50,
) -> MetricCatalogListResponse:
    if workspace_id != get_settings().default_workspace_id:
        raise MetricCatalogError("workspace is not allowed")
    rows = load_metric_catalog_rows(session, domain=domain, limit=limit)
    count_rows = session.execute(
        select(Metric.business_domain_id, func.count())
        .where(Metric.status == "PUBLISHED")
        .group_by(Metric.business_domain_id)
    ).all()
    return MetricCatalogListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        items=[
            build_metric_item(session, metric, business_domain, version, model)
            for metric, business_domain, version, model in rows
        ],
        total=len(rows),
        domain_counts={domain_id: int(count) for domain_id, count in count_rows},
    )


def get_metric_detail(
    session: Session,
    metric_id: str,
    request_id: str,
    trace_id: str,
    workspace_id: str = "demo",
) -> MetricCatalogDetailResponse:
    if workspace_id != get_settings().default_workspace_id:
        raise MetricCatalogError("workspace is not allowed")

    row = session.execute(
        select(Metric, BusinessDomain)
        .join(BusinessDomain, BusinessDomain.id == Metric.business_domain_id)
        .where(Metric.id == metric_id, Metric.status == "PUBLISHED")
    ).one_or_none()
    if row is None:
        raise MetricCatalogError("metric_id does not exist")

    metric, domain = row
    version = latest_published_version(session, metric.id)
    if version is None:
        raise MetricCatalogError("metric has no published version")
    model = session.get(SemanticModel, version.semantic_model_id)
    if model is None:
        raise MetricCatalogError("metric semantic model does not exist")

    return MetricCatalogDetailResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        metric=build_metric_item(session, metric, domain, version, model),
        expression=version.expression_json,
        version_status=version.status,
        published_at=version.published_at,
        versions=[
            MetricCatalogVersion(
                version=item.version,
                status=item.status,
                formula_text=formula_text(item.expression_json or {}),
                semantic_model_id=item.semantic_model_id,
                published_at=item.published_at,
            )
            for item in session.scalars(
                select(MetricVersion)
                .where(
                    MetricVersion.metric_id == metric.id,
                    MetricVersion.status == "PUBLISHED",
                )
                .order_by(MetricVersion.version.desc())
            ).all()
        ],
    )
