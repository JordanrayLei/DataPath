from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db.models import Dimension, MetricVersion, QueryRun, SemanticEntity, SemanticModel
from app.schemas.chatbi import CompileResponse, EstimatedCost, Lineage, QueryDsl
from app.services.signing import create_execution_token
from app.services.access_policy import POLICY_VERSION, policy_for_operator
from app.services.join_planner import expression_model_ids, plan_query_models
from app.warehouse.clickhouse import ClickHouseClient
from app.services.production_benchmark_semantics import MODEL_FIELDS as PRODUCTION_MODEL_FIELDS, MODEL_TABLES as PRODUCTION_MODEL_TABLES


ALLOWED_TABLES = set(PRODUCTION_MODEL_TABLES.values())

ALLOWED_FIELDS = dict(PRODUCTION_MODEL_FIELDS)


class CompilationError(ValueError):
    pass


def hydrate_semantic_allowlists(session: Session) -> None:
    """Load only human-published semantic models into compiler allowlists."""
    models = session.scalars(
        select(SemanticModel).where(SemanticModel.status == "ACTIVE")
    ).all()
    for model in models:
        fields = {str(field) for field in (model.fields_json or []) if str(field)}
        if fields:
            ALLOWED_TABLES.add(model.physical_table)
            ALLOWED_FIELDS[model.id] = fields


def is_cross_fact_expression(session: Session, model_ids: set[str]) -> bool:
    if len(model_ids) < 2:
        return False
    fact_models = set(
        session.scalars(
            select(SemanticEntity.semantic_model_id).where(
                SemanticEntity.semantic_model_id.in_(model_ids),
                SemanticEntity.entity_type == "fact",
                SemanticEntity.status == "ACTIVE",
            )
        ).all()
    )
    return len(fact_models) > 1


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
    if operation in {"sum", "count", "count_distinct"}:
        source_model_id = str(expression.get("source_model_id") or model_id)
        field = require_field(source_model_id, str(expression.get("field", "")))
        lineage_fields.add(field)
        qualified = qualified_field(source_model_id, field, model_aliases)
        if operation == "sum":
            return f"sum({qualified})"
        if operation == "count":
            return f"count({qualified})"
        return f"uniqExact({qualified})"
    if operation == "subtract":
        left = expression.get("left")
        right = expression.get("right")
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise CompilationError("subtract expression requires left and right terms")
        return "(" + compile_metric_expression(
            left, model_id, lineage_fields, model_aliases
        ) + " - " + compile_metric_expression(
            right, model_id, lineage_fields, model_aliases
        ) + ")"
    if operation == "add":
        terms = expression.get("terms")
        if not isinstance(terms, list) or len(terms) < 2:
            raise CompilationError("add expression requires at least two terms")
        compiled_terms = [
            compile_metric_expression(term, model_id, lineage_fields, model_aliases)
            for term in terms
            if isinstance(term, dict)
        ]
        if len(compiled_terms) != len(terms):
            raise CompilationError("add expression terms must be objects")
        return "(" + " + ".join(compiled_terms) + ")"
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


def _render_aggregate_before_join_expression(
    expression: dict,
    default_model_id: str,
    leaves: list[tuple[str, str, str]],
    lineage_fields: set[str],
) -> str:
    """Render a governed cross-fact formula over independently aggregated leaves."""

    operation = expression.get("op")
    if operation in {"sum", "count", "count_distinct"}:
        source_model_id = str(expression.get("source_model_id") or default_model_id)
        field = require_field(source_model_id, str(expression.get("field", "")))
        lineage_fields.add(field)
        alias = f"v{len(leaves)}"
        leaves.append((source_model_id, operation, field))
        return f"a{len(leaves) - 1}.{alias}"
    if operation in {"add", "subtract"}:
        if operation == "add":
            terms = expression.get("terms")
            if not isinstance(terms, list) or len(terms) < 2 or not all(
                isinstance(item, dict) for item in terms
            ):
                raise CompilationError("add expression requires at least two object terms")
            rendered = [
                _render_aggregate_before_join_expression(
                    item, default_model_id, leaves, lineage_fields
                )
                for item in terms
            ]
            return "(" + " + ".join(rendered) + ")"
        left = expression.get("left")
        right = expression.get("right")
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise CompilationError("subtract expression requires left and right terms")
        return "(" + _render_aggregate_before_join_expression(
            left, default_model_id, leaves, lineage_fields
        ) + " - " + _render_aggregate_before_join_expression(
            right, default_model_id, leaves, lineage_fields
        ) + ")"
    if operation == "ratio":
        numerator = expression.get("numerator")
        denominator = expression.get("denominator")
        if not isinstance(numerator, dict) or not isinstance(denominator, dict):
            raise CompilationError("ratio expression requires numerator and denominator")
        numerator_sql = _render_aggregate_before_join_expression(
            numerator, default_model_id, leaves, lineage_fields
        )
        denominator_sql = _render_aggregate_before_join_expression(
            denominator, default_model_id, leaves, lineage_fields
        )
        scale = expression.get("scale", 1)
        if scale not in {1, 100, 1000}:
            raise CompilationError("ratio scale is not allowed")
        return (
            f"round(if({denominator_sql} = 0, NULL, "
            f"toFloat64({numerator_sql}) / toFloat64({denominator_sql}) * {scale}), 2)"
        )
    raise CompilationError(f"unsupported cross-fact metric operation: {operation}")


def _compile_aggregate_before_join(
    session: Session,
    dsl: QueryDsl,
    version: MetricVersion,
    access_policy: Any,
) -> tuple[str, dict[str, Any], list[str], set[str], list[str]]:
    """Compile a scalar multi-fact metric without ever joining fact rows.

    V1 deliberately supports only an ungrouped result.  A requested dimension,
    filter, or multi-metric projection fails closed until a shared-grain contract
    has been published for that exact shape.
    """

    if len(dsl.metrics) != 1:
        raise CompilationError("cross-fact V1 supports exactly one governed metric")
    if dsl.dimensions or dsl.filters:
        raise CompilationError(
            "cross-fact dimensions and filters require a published shared-grain contract"
        )
    if dsl.dsl_version == "2.0" and dsl.query_mode != "multi_fact":
        raise CompilationError("cross-fact metric requires query_mode=multi_fact")

    leaves: list[tuple[str, str, str]] = []
    lineage_fields: set[str] = set()
    expression_sql = _render_aggregate_before_join_expression(
        version.expression_json,
        version.semantic_model_id,
        leaves,
        lineage_fields,
    )
    source_model_ids = {item[0] for item in leaves}
    if len(source_model_ids) < 2:
        raise CompilationError("aggregate-before-join requires at least two fact models")

    models = {
        item.id: item
        for item in session.scalars(
            select(SemanticModel).where(SemanticModel.id.in_(source_model_ids))
        ).all()
    }
    if set(models) != source_model_ids:
        raise CompilationError("cross-fact expression references an unknown semantic model")

    params: dict[str, Any] = {
        "time_start": dsl.time_range.start.isoformat(),
        "time_end_exclusive": (dsl.time_range.end + timedelta(days=1)).isoformat(),
    }
    tenant_placeholders: list[str] = []
    for index, tenant_id in enumerate(access_policy.tenant_ids or ()):
        key = f"acl_tenant_id_{index}"
        params[key] = tenant_id
        tenant_placeholders.append(f"{{{key}:UInt64}}")

    subqueries: list[str] = []
    lineage_tables: list[str] = []
    lineage_models: list[str] = []
    for index, (source_model_id, operation, field) in enumerate(leaves):
        model = models[source_model_id]
        if model.physical_table not in ALLOWED_TABLES:
            raise CompilationError("cross-fact semantic model table is not allowed")
        time_field = require_field(source_model_id, model.default_time_field)
        lineage_fields.add(time_field)
        aggregate = {
            "sum": f"sum({field})",
            "count": f"count({field})",
            "count_distinct": f"uniqExact({field})",
        }[operation]
        where = [
            f"toDate({time_field}) >= {{time_start:Date}}",
            f"toDate({time_field}) < {{time_end_exclusive:Date}}",
        ]
        if tenant_placeholders:
            tenant_field = require_field(source_model_id, "tenant_id")
            where.append(f"{tenant_field} IN ({', '.join(tenant_placeholders)})")
            lineage_fields.add("tenant_id")
        subqueries.append(
            f"a{index} AS (SELECT {aggregate} AS v{index} "
            f"FROM {model.physical_table} WHERE " + " AND ".join(where) + ")"
        )
        lineage_tables.append(model.physical_table)
        lineage_models.append(source_model_id)

    metric_item = dsl.metrics[0]
    output_alias = metric_item.alias or metric_item.metric_id
    sql = "\n".join(
        [
            "WITH",
            "    " + ",\n    ".join(subqueries),
            "SELECT",
            f"    {expression_sql} AS {output_alias}",
            "FROM " + " CROSS JOIN ".join(f"a{index}" for index in range(len(leaves))),
            f"LIMIT {dsl.limit}",
        ]
    )
    return sql, params, list(dict.fromkeys(lineage_tables)), lineage_fields, list(dict.fromkeys(lineage_models))


def _persist_compilation(
    session: Session,
    *,
    dsl: QueryDsl,
    sql: str,
    params: dict[str, Any],
    workspace_id: str,
    operator_id: str,
    request_id: str,
    trace_id: str,
    metric_versions: dict[str, int],
    lineage_models: list[str],
    lineage_tables: list[str],
    lineage_fields: set[str],
    access_policy: Any,
    query_mode: str,
) -> CompileResponse:
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
    unique_tables = list(dict.fromkeys(lineage_tables))
    estimated_rows = sum(clickhouse.estimate_table_rows(item) for item in unique_tables)
    risk_level = "medium" if estimated_rows > 5_000_000 else "low"
    estimated_cost = {
        "risk_level": risk_level,
        "estimated_rows": estimated_rows,
        "estimated_bytes": 0,
    }
    lineage = {
        "models": lineage_models,
        "tables": unique_tables,
        "fields": sorted(lineage_fields),
        "query_mode": query_mode,
        "fanout_strategy": (
            "aggregate_before_join" if query_mode == "multi_fact" else "governed_join"
        ),
        "row_policy": {
            "policy_version": POLICY_VERSION,
            "role_id": access_policy.role_id,
            "scope": access_policy.scope_label,
            "scope_fingerprint": access_policy.scope_fingerprint,
        },
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


def compile_query(
    session: Session,
    dsl: QueryDsl,
    workspace_id: str,
    operator_id: str,
    request_id: str,
    trace_id: str,
) -> CompileResponse:
    hydrate_semantic_allowlists(session)
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

    expression_models = {
        source_model_id
        for key in requested_versions
        for source_model_id in expression_model_ids(
            version_map[key].expression_json, version_map[key].semantic_model_id
        )
    }
    if is_cross_fact_expression(session, expression_models):
        access_policy = policy_for_operator(operator_id)
        if access_policy is None or not access_policy.can_query_business_data:
            raise CompilationError("operator has no business data access policy")
        version = version_map[next(iter(requested_versions))]
        sql, params, lineage_tables, lineage_fields, lineage_models = (
            _compile_aggregate_before_join(session, dsl, version, access_policy)
        )
        return _persist_compilation(
            session,
            dsl=dsl,
            sql=sql,
            params=params,
            workspace_id=workspace_id,
            operator_id=operator_id,
            request_id=request_id,
            trace_id=trace_id,
            metric_versions={item.metric_id: item.metric_version for item in dsl.metrics},
            lineage_models=lineage_models,
            lineage_tables=lineage_tables,
            lineage_fields=lineage_fields,
            access_policy=access_policy,
            query_mode="multi_fact",
        )

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
        "time_end_exclusive": (dsl.time_range.end + timedelta(days=1)).isoformat(),
    }
    time_dimension = dimensions[time_dimension_id]
    time_mapping = time_dimension.mapping_json[model_id]
    time_expression = compile_dimension(
        {**time_mapping, "kind": "field"}, model_id, lineage_fields, model_aliases
    )
    where_parts = [
        f"toDate({time_expression}) >= {{time_start:Date}} AND "
        f"toDate({time_expression}) < {{time_end_exclusive:Date}}"
    ]
    access_policy = policy_for_operator(operator_id)
    if access_policy is None or not access_policy.can_query_business_data:
        raise CompilationError("operator has no business data access policy")
    policy_tables: list[str] = []
    if access_policy.tenant_ids:
        if model_id not in PRODUCTION_MODEL_FIELDS:
            raise CompilationError("tenant row policy is not implemented for this semantic model")
        tenant_expression = qualified_field(
            model_id, require_field(model_id, "tenant_id"), model_aliases
        )
        tenant_placeholders = []
        for index, tenant_id in enumerate(access_policy.tenant_ids):
            key = f"acl_tenant_id_{index}"
            params[key] = tenant_id
            tenant_placeholders.append(f"{{{key}:UInt64}}")
        where_parts.append(
            f"{tenant_expression} IN ({', '.join(tenant_placeholders)})"
        )
        lineage_fields.add("tenant_id")
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

    lineage_tables = [table, *(join.right_table for join in plan.joins), *policy_tables]
    return _persist_compilation(
        session,
        dsl=dsl,
        sql=sql,
        params=params,
        workspace_id=workspace_id,
        operator_id=operator_id,
        request_id=request_id,
        trace_id=trace_id,
        metric_versions=metric_versions,
        lineage_models=list(plan.model_aliases),
        lineage_tables=lineage_tables,
        lineage_fields=lineage_fields,
        access_policy=access_policy,
        query_mode=plan.query_mode,
    )
