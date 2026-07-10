from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db.models import Dimension, Metric, MetricDimension, MetricVersion
from app.schemas.chatbi import DslValidateResponse, QueryDsl, ValidationIssue


def issue(code: str, message: str, field_path: str) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, field_path=field_path)


def validate_dsl(
    session: Session,
    raw_dsl: dict,
    policy_context: dict,
    request_id: str,
    trace_id: str,
) -> DslValidateResponse:
    try:
        dsl = QueryDsl.model_validate(raw_dsl)
    except ValidationError as error:
        issues = [
            issue(
                "SCHEMA_INVALID",
                item["msg"],
                ".".join(str(part) for part in item["loc"]),
            )
            for item in error.errors()[:20]
        ]
        return DslValidateResponse(
            request_id=request_id,
            trace_id=trace_id,
            status="INVALID",
            normalized_dsl=None,
            issues=issues,
            message="Query DSL 结构不合法。",
        )

    metric_keys = [(item.metric_id, item.metric_version) for item in dsl.metrics]
    versions = session.scalars(
        select(MetricVersion)
        .options(joinedload(MetricVersion.metric), joinedload(MetricVersion.semantic_model))
        .where(
            MetricVersion.metric_id.in_([key[0] for key in metric_keys]),
            MetricVersion.status == "PUBLISHED",
        )
    ).all()
    version_map = {(row.metric_id, row.version): row for row in versions}

    issues: list[ValidationIssue] = []
    for index, key in enumerate(metric_keys):
        row = version_map.get(key)
        if row is None or row.metric.status != "PUBLISHED":
            issues.append(
                issue(
                    "METRIC_VERSION_NOT_PUBLISHED",
                    "指标或指标版本不存在或未发布。",
                    f"metrics.{index}",
                )
            )
        elif dsl.metrics[index].aggregation != "default":
            issues.append(
                issue(
                    "AGGREGATION_OVERRIDE_NOT_ALLOWED",
                    "当前指标不允许覆盖默认聚合方式。",
                    f"metrics.{index}.aggregation",
                )
            )

    if issues:
        return DslValidateResponse(
            request_id=request_id,
            trace_id=trace_id,
            status="INVALID",
            normalized_dsl=None,
            issues=issues,
            message="指标或版本校验失败。",
        )

    allowed_domains = set(policy_context.get("allowed_domains", ["sales", "advertising"]))
    denied = [row.metric.business_domain_id for row in version_map.values() if row.metric.business_domain_id not in allowed_domains]
    if denied:
        return DslValidateResponse(
            request_id=request_id,
            trace_id=trace_id,
            status="DENY",
            normalized_dsl=None,
            issues=[issue("RESOURCE_NOT_ALLOWED", "查询包含不可访问资源。", "metrics")],
            message="查询包含不可访问资源。",
        )

    model_ids = {row.semantic_model_id for row in version_map.values()}
    if len(model_ids) != 1:
        issues.append(
            issue(
                "MULTI_MODEL_QUERY_UNSUPPORTED",
                "MVP 暂不支持跨语义模型指标查询。",
                "metrics",
            )
        )

    metric_ids = [item.metric_id for item in dsl.metrics]
    allowed_pairs = set(
        session.execute(
            select(MetricDimension.metric_id, MetricDimension.dimension_id).where(
                MetricDimension.metric_id.in_(metric_ids)
            )
        ).all()
    )
    requested_dimension_ids = [item.dimension_id for item in dsl.dimensions]
    for dimension_id in requested_dimension_ids:
        for metric_id in metric_ids:
            if (metric_id, dimension_id) not in allowed_pairs:
                issues.append(
                    issue(
                        "DIMENSION_NOT_SUPPORTED",
                        "指标不支持所选维度。",
                        f"dimensions.{dimension_id}",
                    )
                )

    dimensions = {
        row.id: row
        for row in session.scalars(
            select(Dimension).where(
                Dimension.id.in_(requested_dimension_ids + [item.field_id for item in dsl.filters]),
                Dimension.status == "ACTIVE",
            )
        ).all()
    }
    model_id = next(iter(model_ids), "")
    for index, query_filter in enumerate(dsl.filters):
        dimension = dimensions.get(query_filter.field_id)
        if dimension is None:
            issues.append(
                issue(
                    "FILTER_FIELD_NOT_ALLOWED",
                    "筛选字段不存在或不是可筛选维度。",
                    f"filters.{index}.field_id",
                )
            )
            continue
        if query_filter.field_id not in requested_dimension_ids and not all(
            (metric_id, query_filter.field_id) in allowed_pairs for metric_id in metric_ids
        ):
            issues.append(
                issue(
                    "FILTER_FIELD_NOT_SUPPORTED",
                    "指标不支持该筛选维度。",
                    f"filters.{index}.field_id",
                )
            )
        if query_filter.operator not in dimension.allowed_operators:
            issues.append(
                issue(
                    "FILTER_OPERATOR_NOT_ALLOWED",
                    "该维度不支持所选筛选操作符。",
                    f"filters.{index}.operator",
                )
            )
        if model_id not in dimension.mapping_json:
            issues.append(
                issue(
                    "DIMENSION_MODEL_MAPPING_MISSING",
                    "维度缺少当前语义模型映射。",
                    f"filters.{index}.field_id",
                )
            )

    allowed_sort_fields = set(metric_ids) | set(requested_dimension_ids)
    for index, sort_item in enumerate(dsl.sort):
        if sort_item.field_id not in allowed_sort_fields:
            issues.append(
                issue(
                    "SORT_FIELD_NOT_SELECTED",
                    "排序字段必须出现在查询指标或维度中。",
                    f"sort.{index}.field_id",
                )
            )

    if (dsl.time_range.end - dsl.time_range.start).days + 1 > get_settings().max_query_days:
        issues.append(
            issue(
                "TIME_RANGE_TOO_LARGE",
                f"时间范围不能超过 {get_settings().max_query_days} 天。",
                "time_range",
            )
        )

    if issues:
        return DslValidateResponse(
            request_id=request_id,
            trace_id=trace_id,
            status="INVALID",
            normalized_dsl=None,
            issues=issues,
            message="Query DSL 业务规则校验失败。",
        )

    normalized = dsl.model_dump(mode="json", exclude_none=True)
    return DslValidateResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="VALID",
        normalized_dsl=normalized,
        issues=[],
        message="",
    )

