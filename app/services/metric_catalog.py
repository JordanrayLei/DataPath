from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import (
    BusinessDomain,
    Dimension,
    Metric,
    MetricAlias,
    MetricDimension,
    MetricSemanticProfile,
    MetricVersion,
    SchemaChangeEvent,
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
from app.services.join_planner import expression_model_ids
from app.services.query_compiler import is_cross_fact_expression


class MetricCatalogError(ValueError):
    pass


def semantic_readiness(
    *,
    description: str,
    owner: str,
    aliases: list[str],
    positive_examples: list[str],
    negative_examples: list[str],
) -> dict[str, Any]:
    """Return an advisory semantic-package score; it never changes metric math."""

    components = {
        "definition": min(20, round(len(description.strip()) / 40 * 20)),
        "aliases": min(25, round(len(set(aliases)) / 5 * 25)),
        "positive_examples": min(25, round(len(set(positive_examples)) / 5 * 25)),
        "negative_examples": min(20, round(len(set(negative_examples)) / 3 * 20)),
        "governance_owner": 10 if owner.strip() else 0,
    }
    score = sum(components.values())
    gaps = []
    if components["definition"] < 20:
        gaps.append("业务定义建议至少 40 个字符，并写明包含项和排除项")
    if len(set(aliases)) < 5:
        gaps.append("至少维护 5 个经过审核的业务别名")
    if len(set(positive_examples)) < 5:
        gaps.append("至少维护 5 条不同句式的正向问法")
    if len(set(negative_examples)) < 3:
        gaps.append("至少维护 3 条相邻指标或易混淆负例")
    return {
        "score": score,
        "status": "READY" if score >= 80 else "NEEDS_WORK" if score >= 50 else "INCOMPLETE",
        "components": components,
        "gaps": gaps,
        "minimum_publish_recommendation": 80,
        "advisory_only": True,
    }


def alias_conflicts(
    session: Session,
    *,
    metric_id: str,
    business_domain_id: str,
    name: str,
    aliases: list[str],
) -> list[dict[str, Any]]:
    """Find exact governed-term collisions with other published metrics."""

    proposed = {
        value.strip().casefold(): value.strip()
        for value in [name, *aliases]
        if value.strip()
    }
    others = session.scalars(
        select(Metric)
        .options(selectinload(Metric.aliases))
        .where(
            Metric.business_domain_id == business_domain_id,
            Metric.id != metric_id,
            Metric.status == "PUBLISHED",
        )
        .order_by(Metric.id)
    ).all()
    conflicts = []
    for other in others:
        other_terms = [other.name, *(row.alias for row in other.aliases)]
        for term in other_terms:
            normalized = term.strip().casefold()
            if normalized and normalized in proposed:
                conflicts.append(
                    {
                        "type": "EXACT_GOVERNED_TERM",
                        "term": proposed[normalized],
                        "other_metric_id": other.id,
                        "other_metric_name": other.name,
                        "message": f"“{proposed[normalized]}”已被 {other.name} 使用",
                    }
                )
    return conflicts


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
    field = expression.get("field")
    if field and expression.get("source_model_id"):
        field = f"{expression['source_model_id']}.{field}"
    if op == "sum":
        return f"SUM({field})"
    if op == "avg":
        return f"AVG({field})"
    if op == "count_distinct":
        return f"COUNT(DISTINCT {field})"
    if op == "count":
        return f"COUNT({field or '*'})"
    if op == "add":
        return " + ".join(
            f"({formula_text(item)})" for item in expression.get("terms", [])
        )
    if op == "subtract":
        left = formula_text(expression.get("left", {}))
        right = formula_text(expression.get("right", {}))
        return f"({left}) - ({right})"
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
    positive_examples = [str(item) for item in ((profile.positive_examples_json if profile else []) or [])]
    negative_examples = [str(item) for item in ((profile.negative_examples_json if profile else []) or [])]
    readiness = semantic_readiness(
        description=metric.description,
        owner=metric.owner,
        aliases=aliases,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
    )
    conflicts = alias_conflicts(
        session,
        metric_id=metric.id,
        business_domain_id=metric.business_domain_id,
        name=metric.name,
        aliases=aliases,
    )
    expression = version.expression_json or {}
    fields = extract_expression_fields(expression)
    source_model_ids = expression_model_ids(expression, model.id)
    source_models = session.scalars(
        select(SemanticModel)
        .where(SemanticModel.id.in_(source_model_ids))
        .order_by(SemanticModel.id)
    ).all()
    governance_blockers: list[str] = []
    if metric.status == "BLOCKED" or domain.status == "DEGRADED":
        events = session.scalars(
            select(SchemaChangeEvent)
            .where(SchemaChangeEvent.status == "OPEN")
            .order_by(SchemaChangeEvent.detected_at.desc())
        ).all()
        for event in events:
            impact = dict(event.impact_json or {})
            if metric.id not in set(impact.get("metric_ids") or []):
                continue
            diff = dict(event.diff_json or {})
            removed = [str(item) for item in (diff.get("removed_columns") or [])]
            type_changes = [
                str(item.get("column") or item.get("name") or item)
                if isinstance(item, dict)
                else str(item)
                for item in (diff.get("type_changes") or [])
            ]
            details = []
            if removed:
                details.append(f"缺失字段：{', '.join(removed)}")
            if type_changes:
                details.append(f"字段类型变化：{', '.join(type_changes)}")
            governance_blockers.append(
                f"{event.change_type}（{event.severity}）"
                + (f" · {'；'.join(details)}" if details else "")
            )
    if metric.status == "BLOCKED" and not governance_blockers:
        governance_blockers.append("指标依赖的模型或关系处于异常状态，需先完成结构变更治理")
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
        positive_examples=positive_examples,
        negative_examples=negative_examples,
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
            "models": [item.id for item in source_models],
            "tables": [item.physical_table for item in source_models],
            "fields": fields,
            "fanout_strategy": (
                "aggregate_before_join"
                if is_cross_fact_expression(session, source_model_ids)
                else "governed_join"
                if len(source_model_ids) > 1
                else "single_model"
            ),
        },
        example_questions=(
            [str(item) for item in (profile.positive_examples_json or [])][:3]
            if profile and profile.positive_examples_json
            else example_questions(metric, dimensions)
        ),
        semantic_readiness=readiness,
        alias_conflicts=conflicts,
        business_domain_status=domain.status,
        semantic_model_status=model.status,
        read_only=(
            metric.status != "PUBLISHED"
            or domain.status != "ACTIVE"
            or model.status != "ACTIVE"
        ),
        governance_blockers=list(dict.fromkeys(governance_blockers)),
    )


def load_metric_catalog_rows(
    session: Session,
    domain: str = "ALL",
    limit: int = 50,
    visibility: str = "runtime",
) -> list[tuple[Metric, BusinessDomain, MetricVersion, SemanticModel]]:
    if limit < 1 or limit > 200:
        raise MetricCatalogError("limit must be between 1 and 200")
    if visibility not in {"runtime", "governance"}:
        raise MetricCatalogError("visibility is invalid")
    if domain != "ALL" and session.get(BusinessDomain, domain) is None:
        raise MetricCatalogError("domain is invalid")

    filters = (
        [
            Metric.status.in_(["PUBLISHED", "BLOCKED"]),
            MetricVersion.status.in_(["PUBLISHED", "BLOCKED"]),
        ]
        if visibility == "governance"
        else [
            Metric.status == "PUBLISHED",
            MetricVersion.status == "PUBLISHED",
        ]
    )
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
    visibility: str = "runtime",
) -> MetricCatalogListResponse:
    if workspace_id != get_settings().default_workspace_id:
        raise MetricCatalogError("workspace is not allowed")
    rows = load_metric_catalog_rows(
        session,
        domain=domain,
        limit=limit,
        visibility=visibility,
    )
    metric_statuses = (
        ["PUBLISHED", "BLOCKED"] if visibility == "governance" else ["PUBLISHED"]
    )
    count_rows = session.execute(
        select(Metric.business_domain_id, func.count())
        .where(Metric.status.in_(metric_statuses))
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
    visibility: str = "runtime",
) -> MetricCatalogDetailResponse:
    if workspace_id != get_settings().default_workspace_id:
        raise MetricCatalogError("workspace is not allowed")

    if visibility not in {"runtime", "governance"}:
        raise MetricCatalogError("visibility is invalid")
    metric_statuses = (
        ["PUBLISHED", "BLOCKED"] if visibility == "governance" else ["PUBLISHED"]
    )
    row = session.execute(
        select(Metric, BusinessDomain)
        .join(BusinessDomain, BusinessDomain.id == Metric.business_domain_id)
        .where(Metric.id == metric_id, Metric.status.in_(metric_statuses))
    ).one_or_none()
    if row is None:
        raise MetricCatalogError("metric_id does not exist")

    metric, domain = row
    version = (
        session.scalar(
            select(MetricVersion)
            .where(
                MetricVersion.metric_id == metric.id,
                MetricVersion.status.in_(["PUBLISHED", "BLOCKED"]),
            )
            .order_by(MetricVersion.version.desc())
            .limit(1)
        )
        if visibility == "governance"
        else latest_published_version(session, metric.id)
    )
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
