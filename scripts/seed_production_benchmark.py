"""Register the clean, definition-only production benchmark metric system.

This seed intentionally contains no aliases, positive/negative examples, scope
examples, ambiguity examples, or feedback-derived policy.  Those assets belong
to the post-baseline governance loop and must be published separately.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.models import (
    BusinessDomain, Dimension, Metric, MetricDimension,
    MetricVersion, SemanticEntity, SemanticJoinRelation,
    SemanticModel, WarehouseSource,
)
from app.db.session import SessionLocal
from app.services.production_benchmark_semantics import (
    DEFAULT_TIME_FIELDS,
    DOMAIN_ID,
    ENTITY_KEYS,
    FACT_MODEL_IDS,
    METRIC_DESCRIPTIONS,
    MODEL_FIELDS,
    MODEL_NAMES,
    MODEL_TABLES,
    PUBLISHED_METRICS,
    RELATIONS,
    STAGED_METRICS,
)


def _entity_id(model_id: str) -> str:
    return model_id.replace("SM_", "E_", 1)


def seed() -> None:
    with SessionLocal() as session:
        domain = session.get(BusinessDomain, DOMAIN_ID)
        values = {
            "name": "全渠道零售运营",
            "description": "覆盖订单、商品、支付、退款、履约、库存、客服和营销的多事实业务域",
            "owner": "data-platform",
            "business_goal": "统一交易、履约、库存、客服和营销的可信经营分析口径",
            "status": "ACTIVE",
        }
        if domain is None:
            session.add(BusinessDomain(id=DOMAIN_ID, **values))
        else:
            for key, value in values.items(): setattr(domain, key, value)
        session.flush()

        source = session.get(WarehouseSource, "production_warehouse")
        source_values = {
            "workspace_id": "demo",
            "name": "Production Benchmark",
            "kind": "clickhouse",
            "business_domain_id": DOMAIN_ID,
            "connection_json": {"database": "production_benchmark"},
            "scan_snapshot_json": {},
            "governance_json": {},
            "status": "PUBLISHED",
            "created_by": "test_fixture",
        }
        if source is None:
            session.add(WarehouseSource(id="production_warehouse", **source_values))
        else:
            for key, value in source_values.items():
                setattr(source, key, value)
        session.flush()

        for model_id, table in MODEL_TABLES.items():
            model = session.get(SemanticModel, model_id)
            values = {"business_domain_id": DOMAIN_ID, "name": MODEL_NAMES[model_id], "warehouse": "clickhouse", "physical_table": table, "default_time_field": DEFAULT_TIME_FIELDS[model_id], "fields_json": sorted(MODEL_FIELDS[model_id]), "status": "ACTIVE"}
            if model is None: session.add(SemanticModel(id=model_id, **values))
            else:
                for key, value in values.items(): setattr(model, key, value)
        session.flush()

        for model_id in MODEL_TABLES:
            entity_id = _entity_id(model_id)
            entity = session.get(SemanticEntity, entity_id)
            entity_type = "fact" if model_id in FACT_MODEL_IDS else "dimension"
            values = {"semantic_model_id": model_id, "business_domain_id": DOMAIN_ID, "name": MODEL_NAMES[model_id], "grain": "governed by production schema contract", "primary_key_json": ENTITY_KEYS[model_id], "entity_type": entity_type, "status": "ACTIVE"}
            if entity is None: session.add(SemanticEntity(id=entity_id, **values))
            else:
                for key, value in values.items(): setattr(entity, key, value)
        session.flush()

        for relation_id, (left, right, left_keys, right_keys, relationship, strategy, status) in RELATIONS.items():
            relation = session.get(SemanticJoinRelation, relation_id)
            values = {"business_domain_id": DOMAIN_ID, "left_entity_id": _entity_id(left), "right_entity_id": _entity_id(right), "left_keys_json": left_keys, "right_keys_json": right_keys, "relationship_type": relationship, "join_type": "left", "fanout_strategy": strategy, "priority": 20, "status": status, "version": 1}
            if relation is None: session.add(SemanticJoinRelation(id=relation_id, **values))
            else:
                for key, value in values.items(): setattr(relation, key, value)

        fact_models = sorted(FACT_MODEL_IDS)
        dimension_specs = {
            "D_DATE": ("日期", "time_grain", "business_date", "day"),
            "D_MONTH": ("月份", "time_grain", "business_date", "month"),
            "D_PROD_REGION": ("业务区域", "enum", "region_code", None),
            "D_PROD_STATUS": ("业务状态", "enum", "status_code", None),
            "D_PROD_CURRENCY": ("币种", "enum", "currency_code", None),
        }
        for dimension_id, (name, kind, field, grain) in dimension_specs.items():
            dimension = session.get(Dimension, dimension_id)
            mapping = {model_id: {"kind": kind if kind == "time_grain" else "field", "field": field, **({"grain": grain} if grain else {})} for model_id in fact_models if field in MODEL_FIELDS[model_id]}
            if dimension is None:
                session.add(Dimension(id=dimension_id, name=name, dimension_type=kind, mapping_json=mapping, allowed_operators=["eq", "neq", "in", "not_in", "between"], status="ACTIVE"))
            else:
                dimension.mapping_json = {**(dimension.mapping_json or {}), **mapping}
        warehouse_dimension = session.get(Dimension, "D_PROD_WAREHOUSE")
        warehouse_mapping = {
            "SM_PROD_SHIPMENTS": {
                "kind": "field",
                "field": "warehouse_id",
                "source_model_id": "SM_PROD_WAREHOUSE",
            }
        }
        if warehouse_dimension is None:
            session.add(Dimension(id="D_PROD_WAREHOUSE", name="仓库", dimension_type="enum", mapping_json=warehouse_mapping, allowed_operators=["eq", "neq", "in", "not_in"], status="ACTIVE"))
        else:
            warehouse_dimension.mapping_json = {**(warehouse_dimension.mapping_json or {}), **warehouse_mapping}

        join_dimension_specs = {
            "D_PROD_PARENT_ORDER_STATUS": (
                "关联订单状态",
                "status_code",
                "SM_PROD_ORDERS",
                {
                    "SM_PROD_ORDER_ITEMS",
                    "SM_PROD_PAYMENTS",
                    "SM_PROD_SHIPMENTS",
                    "SM_PROD_SERVICE_TICKETS",
                },
            ),
            "D_PROD_PARENT_ORDER_REGION": (
                "关联订单区域",
                "region_code",
                "SM_PROD_ORDERS",
                {
                    "SM_PROD_ORDER_ITEMS",
                    "SM_PROD_PAYMENTS",
                    "SM_PROD_SHIPMENTS",
                    "SM_PROD_SERVICE_TICKETS",
                },
            ),
            "D_PROD_PARENT_ORDER_CURRENCY": (
                "关联订单币种",
                "currency_code",
                "SM_PROD_ORDERS",
                {
                    "SM_PROD_ORDER_ITEMS",
                    "SM_PROD_PAYMENTS",
                    "SM_PROD_SHIPMENTS",
                    "SM_PROD_SERVICE_TICKETS",
                },
            ),
            "D_PROD_PARENT_PAYMENT_STATUS": (
                "关联支付状态",
                "status_code",
                "SM_PROD_PAYMENTS",
                {"SM_PROD_REFUNDS"},
            ),
        }
        for dimension_id, (name, field, source_model_id, base_models) in join_dimension_specs.items():
            dimension = session.get(Dimension, dimension_id)
            mapping = {
                model_id: {
                    "kind": "field",
                    "field": field,
                    "source_model_id": source_model_id,
                }
                for model_id in base_models
            }
            if dimension is None:
                session.add(
                    Dimension(
                        id=dimension_id,
                        name=name,
                        dimension_type="enum",
                        mapping_json=mapping,
                        allowed_operators=["eq", "neq", "in", "not_in"],
                        status="ACTIVE",
                    )
                )
            else:
                dimension.name = name
                dimension.mapping_json = mapping
        session.flush()

        dimension_ids = list(dimension_specs)
        for metric_id, name, model_id, metric_type, unit, expression, aliases in PUBLISHED_METRICS:
            if aliases:
                raise ValueError("cold-start seed must not contain metric aliases")
            metric = session.get(Metric, metric_id)
            values = {"business_domain_id": DOMAIN_ID, "name": name, "description": METRIC_DESCRIPTIONS[metric_id], "metric_type": metric_type, "unit": unit, "owner": "data-platform", "status": "PUBLISHED"}
            if metric is None: metric = Metric(id=metric_id, **values); session.add(metric)
            else:
                for key, value in values.items(): setattr(metric, key, value)
            session.flush()
            version = session.scalar(select(MetricVersion).where(MetricVersion.metric_id == metric_id, MetricVersion.version == 1))
            if version is None:
                session.add(MetricVersion(metric_id=metric_id, version=1, semantic_model_id=model_id, expression_json=expression, default_aggregation="default", time_dimension_id="D_DATE", status="PUBLISHED"))
            else:
                version.semantic_model_id = model_id
                version.expression_json = expression
                version.time_dimension_id = "D_DATE"
                version.status = "PUBLISHED"
            for dimension_id in dimension_ids:
                if model_id not in session.get(Dimension, dimension_id).mapping_json:
                    continue
                if session.get(MetricDimension, (metric_id, dimension_id)) is None: session.add(MetricDimension(metric_id=metric_id, dimension_id=dimension_id))
            if metric_id == "M_PROD_SHIPMENT_COUNT" and session.get(MetricDimension, (metric_id, "D_PROD_WAREHOUSE")) is None:
                session.add(MetricDimension(metric_id=metric_id, dimension_id="D_PROD_WAREHOUSE"))
            join_dimensions_by_metric = {
                "M_PROD_ITEM_NET_REVENUE": (
                    "D_PROD_PARENT_ORDER_STATUS",
                    "D_PROD_PARENT_ORDER_REGION",
                    "D_PROD_PARENT_ORDER_CURRENCY",
                ),
                "M_PROD_PAYMENT_AMOUNT": (
                    "D_PROD_PARENT_ORDER_STATUS",
                    "D_PROD_PARENT_ORDER_REGION",
                    "D_PROD_PARENT_ORDER_CURRENCY",
                ),
                "M_PROD_SHIPMENT_COUNT": (
                    "D_PROD_PARENT_ORDER_STATUS",
                    "D_PROD_PARENT_ORDER_REGION",
                    "D_PROD_PARENT_ORDER_CURRENCY",
                ),
                "M_PROD_SERVICE_TICKET_COUNT": (
                    "D_PROD_PARENT_ORDER_STATUS",
                    "D_PROD_PARENT_ORDER_REGION",
                    "D_PROD_PARENT_ORDER_CURRENCY",
                ),
                "M_PROD_REFUND_AMOUNT": ("D_PROD_PARENT_PAYMENT_STATUS",),
            }
            for dimension_id in join_dimensions_by_metric.get(metric_id, ()):
                if session.get(MetricDimension, (metric_id, dimension_id)) is None:
                    session.add(
                        MetricDimension(metric_id=metric_id, dimension_id=dimension_id)
                    )

        for metric_id, name, model_id, expression, reason in STAGED_METRICS:
            metric = session.get(Metric, metric_id)
            if metric is not None and metric.status == "PUBLISHED":
                continue
            values = {"business_domain_id": DOMAIN_ID, "name": name, "description": reason, "metric_type": "ratio" if metric_id.endswith("RATE") else "amount", "unit": "%" if metric_id.endswith("RATE") else "CNY", "owner": "data-platform", "status": "STAGED"}
            if metric is None: session.add(Metric(id=metric_id, **values))
            else:
                for key, value in values.items(): setattr(metric, key, value)
            session.flush()
            version = session.scalar(select(MetricVersion).where(MetricVersion.metric_id == metric_id, MetricVersion.version == 1))
            if version is None:
                session.add(MetricVersion(metric_id=metric_id, version=1, semantic_model_id=model_id, expression_json=expression, default_aggregation="default", time_dimension_id="D_DATE", status="STAGED"))
            else:
                version.semantic_model_id = model_id
                version.expression_json = expression
                version.time_dimension_id = "D_DATE"
                version.status = "STAGED"
        session.commit()
    print("Registered clean definition-only metric system: 11 models, 6 published safe joins, 9 published metrics, 2 staged metrics, 0 governance examples")


if __name__ == "__main__":
    seed()
