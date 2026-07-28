from __future__ import annotations

import copy
import re

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db.models import Dimension, Metric, MetricDimension, MetricVersion
from app.schemas.chatbi import DslValidateResponse, QueryDsl, ValidationIssue
from app.services.join_planner import JoinPlanningError, expression_model_ids, plan_query_models
from app.services.query_compiler import is_cross_fact_expression


def issue(code: str, message: str, field_path: str) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, field_path=field_path)


def normalize_report_usage_time_grain(raw_dsl: dict, query: str) -> dict:
    """Remove an LLM-invented month grain from report-usage language only."""

    normalized_query = " ".join(query.strip().split()).casefold()
    usage_only_monthly = bool(
        re.search(r"用于.{0,20}月度(?:复盘|报告|周报|会议)", normalized_query)
    )
    explicit_monthly_grouping = any(
        token in normalized_query
        for token in ("按月", "每月", "逐月", "月份", "月度趋势", "monthly trend")
    )
    if not usage_only_monthly or explicit_monthly_grouping:
        return raw_dsl
    dimensions = raw_dsl.get("dimensions")
    if not isinstance(dimensions, list) or not any(
        isinstance(item, dict) and item.get("dimension_id") == "D_MONTH"
        for item in dimensions
    ):
        return raw_dsl

    normalized = copy.deepcopy(raw_dsl)
    normalized["dimensions"] = [
        item
        for item in normalized.get("dimensions", [])
        if not (isinstance(item, dict) and item.get("dimension_id") == "D_MONTH")
    ]
    normalized["sort"] = [
        item
        for item in normalized.get("sort", [])
        if not (isinstance(item, dict) and item.get("field_id") == "D_MONTH")
    ]
    if normalized.get("intent") == "trend_query" and not normalized["dimensions"]:
        normalized["intent"] = "aggregate_query"
    return normalized


def validate_dsl(
    session: Session,
    raw_dsl: dict,
    policy_context: dict,
    request_id: str,
    trace_id: str,
    query: str = "",
) -> DslValidateResponse:
    raw_dsl = normalize_report_usage_time_grain(raw_dsl, query)
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
    normalized_query_mode = dsl.query_mode
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

    allowed_domains = set(policy_context.get("allowed_domains", ["production_benchmark"]))
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
                "V1 暂不支持多个事实模型的指标组合查询。",
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

    time_dimension_ids = {row.time_dimension_id for row in version_map.values()}
    all_dimension_ids = set(requested_dimension_ids) | {
        item.field_id for item in dsl.filters
    } | time_dimension_ids
    dimensions = {
        row.id: row
        for row in session.scalars(
            select(Dimension).where(
                Dimension.id.in_(all_dimension_ids),
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

    if len(model_ids) == 1 and not issues:
        required_model_ids = {model_id}
        expression_source_models = {model_id}
        for row in version_map.values():
            sources = expression_model_ids(row.expression_json, model_id)
            required_model_ids.update(sources)
            expression_source_models.update(sources)
        for dimension_id in all_dimension_ids:
            dimension = dimensions.get(dimension_id)
            if dimension is None or model_id not in dimension.mapping_json:
                issues.append(
                    issue(
                        "DIMENSION_MODEL_MAPPING_MISSING",
                        "维度缺少指标事实模型映射。",
                        f"dimensions.{dimension_id}",
                    )
                )
                continue
            mapping = dimension.mapping_json[model_id]
            required_model_ids.add(str(mapping.get("source_model_id") or model_id))
        is_cross_fact = is_cross_fact_expression(session, expression_source_models)
        if is_cross_fact:
            if len(metric_ids) != 1:
                issues.append(
                    issue(
                        "MULTI_FACT_METRIC_COUNT_UNSUPPORTED",
                        "跨事实 V1 每次只允许查询一个已治理指标。",
                        "metrics",
                    )
                )
            if dsl.dimensions or dsl.filters:
                issues.append(
                    issue(
                        "MULTI_FACT_SHARED_GRAIN_NOT_PUBLISHED",
                        "该跨事实指标尚未发布所选维度或筛选的共享粒度契约。",
                        "dimensions",
                    )
                )
            if dsl.dsl_version == "2.0":
                normalized_query_mode = "multi_fact"
        elif not issues:
            try:
                plan = plan_query_models(session, model_id, required_model_ids)
                if dsl.dsl_version == "2.0":
                    normalized_query_mode = plan.query_mode
            except JoinPlanningError as error:
                issues.append(issue("JOIN_PATH_NOT_SAFE", str(error), "dimensions"))

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
    # query_mode is an execution-plan output, not an LLM authority.  The
    # deterministic planner has already proved that every required model is
    # connected by a published safe join, so expose its result downstream.
    normalized["query_mode"] = normalized_query_mode
    # Unordered grouped results are unstable across executions and cannot be
    # compared reliably.  When the user did not request ranking, establish a
    # canonical dimension order without changing the selected rows or metric.
    if requested_dimension_ids and not normalized["sort"]:
        time_grains = {"D_DATE", "D_WEEK", "D_MONTH", "D_QUARTER"}
        if dsl.intent == "trend_query" or requested_dimension_ids[0] in time_grains:
            normalized["sort"] = [
                {"field_id": requested_dimension_ids[0], "direction": "asc"}
            ]
        else:
            normalized["sort"] = [
                {"field_id": metric_ids[0], "direction": "desc"},
                {"field_id": requested_dimension_ids[0], "direction": "asc"},
            ]
    # Keep Dify and the deterministic entrypoint on the same governed result
    # window.  Explicit TopN values below 100 remain intact; larger LLM-picked
    # defaults cannot silently expand execution or change the result contract.
    normalized["limit"] = min(int(normalized["limit"]), 100)
    return DslValidateResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="VALID",
        normalized_dsl=normalized,
        issues=[],
        message="",
    )
