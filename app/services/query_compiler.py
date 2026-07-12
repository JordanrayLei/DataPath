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
from app.services.join_planner import expression_model_ids, plan_query_models
from app.warehouse.clickhouse import ClickHouseClient


ALLOWED_TABLES = {
    "data_warehouse.olist_orders",
    "data_warehouse.olist_order_items",
    "data_warehouse.olist_order_payments",
    "data_warehouse.olist_order_reviews",
    "data_warehouse.olist_customers",
    "data_warehouse.olist_products",
    "data_warehouse.olist_sellers",
    "data_warehouse.olist_geolocation",
    "data_warehouse.olist_product_category_translation",
}

ALLOWED_FIELDS = {
    "SM_OLIST_ORDERS": {
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    },
    "SM_OLIST_ORDER_ITEMS": {
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    },
    "SM_OLIST_PAYMENTS": {
        "order_id", "payment_sequential", "payment_type", "payment_installments",
        "payment_value",
    },
    "SM_OLIST_REVIEWS": {
        "review_id", "order_id", "review_score", "review_comment_title",
        "review_comment_message", "review_creation_date", "review_answer_timestamp",
    },
    "SM_OLIST_CUSTOMERS": {
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state",
    },
    "SM_OLIST_PRODUCTS": {
        "product_id", "product_category_name", "product_name_lenght",
        "product_description_lenght", "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    },
    "SM_OLIST_SELLERS": {
        "seller_id", "seller_zip_code_prefix", "seller_city", "seller_state",
    },
    "SM_OLIST_GEOLOCATION": {
        "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
        "geolocation_city", "geolocation_state",
    },
    "SM_OLIST_CATEGORY_TRANSLATION": {
        "product_category_name", "product_category_name_english",
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


def qualified_field(model_id: str, field: str, model_aliases: dict[str, str] | None) -> str:
    alias = (model_aliases or {}).get(model_id, "")
    return f"{alias}.{field}" if alias else field


def compile_metric_expression(
    expression: dict,
    model_id: str,
    lineage_fields: set[str],
    model_aliases: dict[str, str] | None = None,
) -> str:
    operation = expression.get("op")
    if operation in {"sum", "count_distinct"}:
        source_model_id = str(expression.get("source_model_id") or model_id)
        field = require_field(source_model_id, str(expression.get("field", "")))
        lineage_fields.add(field)
        qualified = qualified_field(source_model_id, field, model_aliases)
        return f"sum({qualified})" if operation == "sum" else f"uniqExact({qualified})"
    if operation == "ratio":
        numerator = compile_metric_expression(
            expression["numerator"], model_id, lineage_fields, model_aliases
        )
        denominator = compile_metric_expression(
            expression["denominator"], model_id, lineage_fields, model_aliases
        )
        scale = expression.get("scale", 1)
        if scale not in {1, 100, 1000}:
            raise CompilationError("ratio scale is not allowed")
        return (
            f"round(if({denominator} = 0, NULL, "
            f"toFloat64({numerator}) / toFloat64({denominator}) * {scale}), 2)"
        )
    raise CompilationError(f"unsupported metric operation: {operation}")


def compile_dimension(
    mapping: dict,
    model_id: str,
    lineage_fields: set[str],
    model_aliases: dict[str, str] | None = None,
) -> str:
    source_model_id = str(mapping.get("source_model_id") or model_id)
    field = require_field(source_model_id, str(mapping.get("field", "")))
    lineage_fields.add(field)
    qualified = qualified_field(source_model_id, field, model_aliases)
    if mapping.get("kind") == "field":
        return qualified
    if mapping.get("kind") == "time_grain" and mapping.get("grain") == "day":
        return f"toDate({qualified})"
    if mapping.get("kind") == "time_grain" and mapping.get("grain") == "month":
        return f"toStartOfMonth({qualified})"
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
    if not requested_versions.issubset(version_map):
        raise CompilationError("metric version changed or is not published")

    model_ids = {version_map[key].semantic_model_id for key in requested_versions}
    if len(model_ids) != 1:
        raise CompilationError("multi-fact metric queries are not supported in V1")
    model_id = next(iter(model_ids))
    semantic_model = versions[0].semantic_model
    table = semantic_model.physical_table
    if table not in ALLOWED_TABLES:
        raise CompilationError("semantic model table is not allowed")

    dimension_ids = {item.dimension_id for item in dsl.dimensions} | {
        item.field_id for item in dsl.filters
    }
    time_dimension_ids = {
        version_map[key].time_dimension_id for key in requested_versions
    }
    if len(time_dimension_ids) != 1:
        raise CompilationError("metrics must share one governed time dimension")
    time_dimension_id = next(iter(time_dimension_ids))
    dimension_ids.add(time_dimension_id)
    dimensions = {
        item.id: item
        for item in session.scalars(
            select(Dimension).where(Dimension.id.in_(dimension_ids))
        ).all()
    }

    required_model_ids = {model_id}
    for key in requested_versions:
        required_model_ids.update(
            expression_model_ids(version_map[key].expression_json, model_id)
        )
    for dimension_id in dimension_ids:
        dimension = dimensions.get(dimension_id)
        if dimension is None or model_id not in dimension.mapping_json:
            raise CompilationError(f"dimension mapping missing: {dimension_id}")
        mapping = dimension.mapping_json[model_id]
        required_model_ids.add(str(mapping.get("source_model_id") or model_id))

    plan = plan_query_models(session, model_id, required_model_ids)
    if dsl.dsl_version == "2.0" and dsl.query_mode != plan.query_mode:
        raise CompilationError(
            f"query mode mismatch: requested {dsl.query_mode}, planned {plan.query_mode}"
        )
    if dsl.query_mode == "multi_fact":
        raise CompilationError("multi-fact queries require aggregate-before-join and are not enabled")
    model_aliases = plan.model_aliases if plan.joins else None

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
            dimension.mapping_json[model_id], model_id, lineage_fields, model_aliases
        )
        alias = item.alias or item.dimension_id
        select_parts.append(f"{expression} AS {alias}")
        group_parts.append(expression)
        output_fields.add(alias)
        dimension_expressions[item.dimension_id] = expression

    metric_versions: dict[str, int] = {}
    for item in dsl.metrics:
        version = version_map[(item.metric_id, item.metric_version)]
        expression = compile_metric_expression(
            version.expression_json, model_id, lineage_fields, model_aliases
        )
        alias = item.alias or item.metric_id
        select_parts.append(f"{expression} AS {alias}")
        output_fields.add(alias)
        metric_versions[item.metric_id] = item.metric_version

    params: dict[str, Any] = {
        "time_start": dsl.time_range.start.isoformat(),
        "time_end": dsl.time_range.end.isoformat(),
    }
    time_dimension = dimensions[time_dimension_id]
    time_mapping = time_dimension.mapping_json[model_id]
    time_expression = compile_dimension(
        {**time_mapping, "kind": "field"}, model_id, lineage_fields, model_aliases
    )
    where_parts = [
        f"{time_expression} BETWEEN {{time_start:Date}} AND {{time_end:Date}}"
    ]

    param_index = 0
    for query_filter in dsl.filters:
        dimension = dimensions.get(query_filter.field_id)
        if dimension is None or model_id not in dimension.mapping_json:
            raise CompilationError(f"filter dimension mapping missing: {query_filter.field_id}")
        expression = compile_dimension(
            dimension.mapping_json[model_id], model_id, lineage_fields, model_aliases
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

    base_alias = plan.model_aliases.get(model_id, "")
    from_clause = f"{table} AS {base_alias}" if base_alias else table
    join_lines: list[str] = []
    for join in plan.joins:
        left_alias = plan.model_aliases[join.left_model_id]
        right_alias = plan.model_aliases[join.right_model_id]
        conditions = []
        for left_key, right_key in zip(join.left_keys, join.right_keys, strict=True):
            require_field(join.left_model_id, left_key)
            require_field(join.right_model_id, right_key)
            lineage_fields.update({left_key, right_key})
            conditions.append(f"{left_alias}.{left_key} = {right_alias}.{right_key}")
        join_lines.append(
            f"{join.join_type.upper()} JOIN {join.right_table} AS {right_alias} ON "
            + " AND ".join(conditions)
        )

    sql_lines = [
        "SELECT",
        "    " + ",\n    ".join(select_parts),
        f"FROM {from_clause}",
        *join_lines,
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
    lineage_tables = [table, *(join.right_table for join in plan.joins)]
    estimated_rows = sum(
        clickhouse.estimate_table_rows(item) for item in dict.fromkeys(lineage_tables)
    )
    risk_level = "medium" if estimated_rows > 5_000_000 else "low"
    estimated_cost = {
        "risk_level": risk_level,
        "estimated_rows": estimated_rows,
        "estimated_bytes": 0,
    }
    lineage = {
        "models": list(plan.model_aliases),
        "tables": list(dict.fromkeys(lineage_tables)),
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
