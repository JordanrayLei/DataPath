from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db.models import Dimension, MetricVersion, QueryRun
from app.schemas.chatbi import CompileResponse, EstimatedCost, Lineage, QueryDsl
from app.services.signing import create_execution_token
from app.warehouse.clickhouse import ClickHouseClient


ALLOWED_TABLES = {
    "data_warehouse.dwd_sales_order_item",
    "data_warehouse.dwd_ad_delivery_day",
}

ALLOWED_FIELDS = {
    "SM_SALES_ORDER_ITEM": {
        "biz_date",
        "order_id",
        "gross_amount",
        "paid_amount",
        "net_revenue",
        "gross_profit",
        "region",
        "province",
        "sales_channel",
        "product_name",
        "category_name",
    },
    "SM_AD_DELIVERY_DAY": {
        "biz_date",
        "ad_platform",
        "ad_account",
        "campaign_name",
        "device_type",
        "attribution_window",
        "spend",
        "attributed_revenue",
    },
}


class CompilationError(ValueError):
    pass


def sha256_json(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(serialized.encode()).hexdigest()}"


def require_field(model_id: str, field: str) -> str:
    if field not in ALLOWED_FIELDS.get(model_id, set()):
        raise CompilationError(f"field is not allowed for model {model_id}")
    return field


def compile_metric_expression(expression: dict, model_id: str, lineage_fields: set[str]) -> str:
    operation = expression.get("op")
    if operation in {"sum", "count_distinct"}:
        field = require_field(model_id, str(expression.get("field", "")))
        lineage_fields.add(field)
        return f"sum({field})" if operation == "sum" else f"uniqExact({field})"
    if operation == "ratio":
        numerator = compile_metric_expression(expression["numerator"], model_id, lineage_fields)
        denominator = compile_metric_expression(expression["denominator"], model_id, lineage_fields)
        scale = expression.get("scale", 1)
        if scale not in {1, 100, 1000}:
            raise CompilationError("ratio scale is not allowed")
        return (
            f"round(if({denominator} = 0, NULL, "
            f"toFloat64({numerator}) / toFloat64({denominator}) * {scale}), 2)"
        )
    raise CompilationError(f"unsupported metric operation: {operation}")


def compile_dimension(mapping: dict, model_id: str, lineage_fields: set[str]) -> str:
    field = require_field(model_id, str(mapping.get("field", "")))
    lineage_fields.add(field)
    if mapping.get("kind") == "field":
        return field
    if mapping.get("kind") == "time_grain" and mapping.get("grain") == "month":
        return f"toStartOfMonth({field})"
    raise CompilationError("unsupported dimension mapping")


def compile_query(
    session: Session,
    dsl: QueryDsl,
    workspace_id: str,
    operator_id: str,
    request_id: str,
    trace_id: str,
) -> CompileResponse:
    versions = session.scalars(
        select(MetricVersion)
        .options(joinedload(MetricVersion.metric), joinedload(MetricVersion.semantic_model))
        .where(
            MetricVersion.metric_id.in_([item.metric_id for item in dsl.metrics]),
            MetricVersion.status == "PUBLISHED",
        )
    ).all()
    version_map = {(item.metric_id, item.version): item for item in versions}
    requested_versions = {(item.metric_id, item.metric_version) for item in dsl.metrics}
    if set(version_map) != requested_versions:
        raise CompilationError("metric version changed or is not published")

    model_ids = {item.semantic_model_id for item in versions}
    if len(model_ids) != 1:
        raise CompilationError("cross-model queries are not supported in MVP")
    model_id = next(iter(model_ids))
    semantic_model = versions[0].semantic_model
    table = semantic_model.physical_table
    if table not in ALLOWED_TABLES:
        raise CompilationError("semantic model table is not allowed")

    dimension_ids = {item.dimension_id for item in dsl.dimensions} | {
        item.field_id for item in dsl.filters
    }
    dimensions = {
        item.id: item
        for item in session.scalars(
            select(Dimension).where(Dimension.id.in_(dimension_ids))
        ).all()
    }

    lineage_fields: set[str] = set()
    select_parts: list[str] = []
    group_parts: list[str] = []
    output_fields: set[str] = set()
    dimension_expressions: dict[str, str] = {}
    for item in dsl.dimensions:
        dimension = dimensions.get(item.dimension_id)
        if dimension is None or model_id not in dimension.mapping_json:
            raise CompilationError(f"dimension mapping missing: {item.dimension_id}")
        expression = compile_dimension(
            dimension.mapping_json[model_id], model_id, lineage_fields
        )
        alias = item.alias or item.dimension_id
        select_parts.append(f"{expression} AS {alias}")
        group_parts.append(expression)
        output_fields.add(alias)
        dimension_expressions[item.dimension_id] = expression

    metric_versions: dict[str, int] = {}
    for item in dsl.metrics:
        version = version_map[(item.metric_id, item.metric_version)]
        expression = compile_metric_expression(version.expression_json, model_id, lineage_fields)
        alias = item.alias or item.metric_id
        select_parts.append(f"{expression} AS {alias}")
        output_fields.add(alias)
        metric_versions[item.metric_id] = item.metric_version

    params: dict[str, Any] = {
        "time_start": dsl.time_range.start.isoformat(),
        "time_end": dsl.time_range.end.isoformat(),
    }
    time_field = require_field(model_id, semantic_model.default_time_field)
    lineage_fields.add(time_field)
    where_parts = [f"{time_field} BETWEEN {{time_start:Date}} AND {{time_end:Date}}"]

    param_index = 0
    for query_filter in dsl.filters:
        dimension = dimensions.get(query_filter.field_id)
        if dimension is None or model_id not in dimension.mapping_json:
            raise CompilationError(f"filter dimension mapping missing: {query_filter.field_id}")
        expression = compile_dimension(
            dimension.mapping_json[model_id], model_id, lineage_fields
        )
        operator = query_filter.operator
        if operator in {"eq", "neq"}:
            key = f"p{param_index}"
            param_index += 1
            params[key] = query_filter.values[0]
            sql_operator = "=" if operator == "eq" else "!="
            where_parts.append(f"{expression} {sql_operator} {{{key}:String}}")
        elif operator in {"in", "not_in"}:
            placeholders = []
            for value in query_filter.values:
                key = f"p{param_index}"
                param_index += 1
                params[key] = value
                placeholders.append(f"{{{key}:String}}")
            sql_operator = "IN" if operator == "in" else "NOT IN"
            where_parts.append(f"{expression} {sql_operator} ({', '.join(placeholders)})")
        else:
            raise CompilationError(f"filter operator is not implemented in MVP: {operator}")

    sql_lines = [
        "SELECT",
        "    " + ",\n    ".join(select_parts),
        f"FROM {table}",
        "WHERE " + " AND ".join(where_parts),
    ]
    if group_parts:
        sql_lines.append("GROUP BY " + ", ".join(group_parts))

    if dsl.sort:
        order_parts = []
        requested_aliases = {
            item.dimension_id: item.alias or item.dimension_id for item in dsl.dimensions
        } | {item.metric_id: item.alias or item.metric_id for item in dsl.metrics}
        for item in dsl.sort:
            alias = requested_aliases.get(item.field_id)
            if alias is None or alias not in output_fields:
                raise CompilationError("sort field is not selected")
            order_parts.append(f"{alias} {item.direction.upper()}")
        sql_lines.append("ORDER BY " + ", ".join(order_parts))
    sql_lines.append(f"LIMIT {dsl.limit}")
    sql = "\n".join(sql_lines)

    dsl_json = dsl.model_dump(mode="json", exclude_none=True)
    dsl_hash = sha256_json(dsl_json)
    sql_fingerprint = sha256_json({"sql": sql, "params": params})
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=get_settings().query_ttl_seconds)
    query_id = f"Q{now.strftime('%Y%m%d%H%M%S')}{secrets.token_hex(5).upper()}"

    clickhouse = ClickHouseClient(
        get_settings().clickhouse_host,
        get_settings().clickhouse_http_port,
        get_settings().clickhouse_compiler_user,
        get_settings().clickhouse_compiler_password,
    )
    estimated_rows = clickhouse.estimate_table_rows(table)
    risk_level = "medium" if estimated_rows > 5_000_000 else "low"
    estimated_cost = {
        "risk_level": risk_level,
        "estimated_rows": estimated_rows,
        "estimated_bytes": 0,
    }
    lineage = {
        "models": [model_id],
        "tables": [table],
        "fields": sorted(lineage_fields),
    }
    execution_token = create_execution_token(
        query_id,
        sql_fingerprint,
        str(int(expires_at.timestamp())),
        get_settings().signing_secret,
    )

    session.add(
        QueryRun(
            query_id=query_id,
            request_id=request_id,
            trace_id=trace_id,
            workspace_id=workspace_id,
            operator_id=operator_id,
            dsl_json=dsl_json,
            dsl_hash=dsl_hash,
            sql_text=sql,
            sql_params=params,
            sql_fingerprint=sql_fingerprint,
            metric_versions=metric_versions,
            lineage_json=lineage,
            estimated_cost=estimated_cost,
            status="READY",
            expires_at=expires_at,
        )
    )
    session.commit()

    return CompileResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="READY",
        query_id=query_id,
        sql_fingerprint=sql_fingerprint,
        dsl_hash=dsl_hash,
        metric_versions=metric_versions,
        lineage=Lineage.model_validate(lineage),
        estimated_cost=EstimatedCost.model_validate(estimated_cost),
        execution_token=execution_token,
        expires_at=expires_at,
        message="",
    )
