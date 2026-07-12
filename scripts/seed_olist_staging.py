"""Register the Olist join graph and publish the safe V1 multi-entity metrics."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models import (
    BusinessDomain,
    Dimension,
    Metric,
    MetricAlias,
    MetricDimension,
    MetricSemanticProfile,
    MetricVersion,
    SemanticEntity,
    SemanticJoinRelation,
    SemanticModel,
    SemanticScopeExample,
)
from app.db.session import SessionLocal
from app.services.metric_vector_index import source_hash


OLIST_MODELS = {
    "SM_OLIST_ORDERS": ("Olist订单", "data_warehouse.olist_orders", "order_purchase_timestamp", "ACTIVE"),
    "SM_OLIST_ORDER_ITEMS": ("Olist订单商品", "data_warehouse.olist_order_items", "shipping_limit_date", "ACTIVE"),
    "SM_OLIST_PAYMENTS": ("Olist支付", "data_warehouse.olist_order_payments", "", "STAGED"),
    "SM_OLIST_REVIEWS": ("Olist订单评价", "data_warehouse.olist_order_reviews", "review_creation_date", "STAGED"),
    "SM_OLIST_CUSTOMERS": ("Olist客户", "data_warehouse.olist_customers", "", "ACTIVE"),
    "SM_OLIST_PRODUCTS": ("Olist商品", "data_warehouse.olist_products", "", "ACTIVE"),
    "SM_OLIST_SELLERS": ("Olist卖家", "data_warehouse.olist_sellers", "", "ACTIVE"),
    "SM_OLIST_GEOLOCATION": ("Olist地理位置", "data_warehouse.olist_geolocation", "", "STAGED"),
    "SM_OLIST_CATEGORY_TRANSLATION": (
        "Olist商品品类翻译",
        "data_warehouse.olist_product_category_translation",
        "",
        "ACTIVE",
    ),
}

ENTITIES = {
    "E_OLIST_ORDER_ITEMS": ("SM_OLIST_ORDER_ITEMS", "订单商品", "one row per order_id and order_item_id", ["order_id", "order_item_id"], "fact", "ACTIVE"),
    "E_OLIST_ORDERS": ("SM_OLIST_ORDERS", "订单", "one row per order_id", ["order_id"], "fact", "ACTIVE"),
    "E_OLIST_PAYMENTS": ("SM_OLIST_PAYMENTS", "支付", "one row per order_id and payment_sequential", ["order_id", "payment_sequential"], "fact", "STAGED"),
    "E_OLIST_REVIEWS": ("SM_OLIST_REVIEWS", "评价", "one row per review_id and order_id", ["review_id", "order_id"], "fact", "STAGED"),
    "E_OLIST_CUSTOMERS": ("SM_OLIST_CUSTOMERS", "客户", "one row per customer_id", ["customer_id"], "dimension", "ACTIVE"),
    "E_OLIST_PRODUCTS": ("SM_OLIST_PRODUCTS", "商品", "one row per product_id", ["product_id"], "dimension", "ACTIVE"),
    "E_OLIST_SELLERS": ("SM_OLIST_SELLERS", "卖家", "one row per seller_id", ["seller_id"], "dimension", "ACTIVE"),
    "E_OLIST_GEOLOCATION": ("SM_OLIST_GEOLOCATION", "地理位置", "multiple rows per zip code prefix", ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"], "bridge", "STAGED"),
    "E_OLIST_CATEGORY_TRANSLATION": ("SM_OLIST_CATEGORY_TRANSLATION", "商品品类翻译", "one row per Portuguese category name", ["product_category_name"], "dimension", "ACTIVE"),
}

RELATIONS = {
    "J_OLIST_ITEMS_ORDERS": ("E_OLIST_ORDER_ITEMS", "E_OLIST_ORDERS", ["order_id"], ["order_id"], "many_to_one", "left", "safe", "PUBLISHED", 10),
    "J_OLIST_ITEMS_PRODUCTS": ("E_OLIST_ORDER_ITEMS", "E_OLIST_PRODUCTS", ["product_id"], ["product_id"], "many_to_one", "left", "safe", "PUBLISHED", 20),
    "J_OLIST_ITEMS_SELLERS": ("E_OLIST_ORDER_ITEMS", "E_OLIST_SELLERS", ["seller_id"], ["seller_id"], "many_to_one", "left", "safe", "PUBLISHED", 20),
    "J_OLIST_ORDERS_CUSTOMERS": ("E_OLIST_ORDERS", "E_OLIST_CUSTOMERS", ["customer_id"], ["customer_id"], "many_to_one", "left", "safe", "PUBLISHED", 20),
    "J_OLIST_PRODUCTS_CATEGORY": ("E_OLIST_PRODUCTS", "E_OLIST_CATEGORY_TRANSLATION", ["product_category_name"], ["product_category_name"], "many_to_one", "left", "safe", "PUBLISHED", 30),
    "J_OLIST_PAYMENTS_ORDERS": ("E_OLIST_PAYMENTS", "E_OLIST_ORDERS", ["order_id"], ["order_id"], "many_to_one", "left", "aggregate_before_join", "STAGED", 50),
    "J_OLIST_REVIEWS_ORDERS": ("E_OLIST_REVIEWS", "E_OLIST_ORDERS", ["order_id"], ["order_id"], "many_to_one", "left", "aggregate_before_join", "STAGED", 50),
}

DIMENSIONS = {
    "D_OLIST_CATEGORY": ("商品品类", "enum", "SM_OLIST_CATEGORY_TRANSLATION", "product_category_name_english"),
    "D_OLIST_CUSTOMER_STATE": ("客户州", "enum", "SM_OLIST_CUSTOMERS", "customer_state"),
    "D_OLIST_SELLER_STATE": ("卖家州", "enum", "SM_OLIST_SELLERS", "seller_state"),
    "D_OLIST_ORDER_STATUS": ("订单状态", "enum", "SM_OLIST_ORDERS", "order_status"),
}

METRICS = [
    ("M_OLIST_ITEM_REVENUE", "Olist商品销售额", "Olist订单商品价格之和，不包含运费。", "amount", "BRL", {"op": "sum", "field": "price"}, ["Olist销售额", "Olist商品金额", "巴西电商销售额"], ["各商品品类Olist销售额", "各客户州Olist销售额", "各卖家州Olist销售额"]),
    ("M_OLIST_FREIGHT_VALUE", "Olist运费", "Olist订单商品行运费之和。", "amount", "BRL", {"op": "sum", "field": "freight_value"}, ["Olist物流费", "Olist配送费"], ["各州Olist运费", "各品类配送费"]),
    ("M_OLIST_ORDER_COUNT", "Olist订单量", "Olist订单商品事实中去重订单数。", "count", "order", {"op": "count_distinct", "field": "order_id"}, ["Olist订单数", "巴西电商订单量"], ["各客户州Olist订单量", "各订单状态订单数"]),
]

OUT_OF_SCOPE_EXAMPLES = [
    ("商品成本、毛利额或毛利率是多少", "Olist不包含商品成本字段"),
    ("广告曝光、点击、投放费用或广告投产比", "Olist不包含广告投放数据"),
    ("库存余额或库存周转天数", "Olist不包含库存快照"),
    ("优惠券领取或核销率", "Olist不包含优惠券数据"),
    ("客户年龄、性别或其他人口属性", "Olist客户数据不包含人口属性"),
    ("渠道获客成本", "Olist不包含获客费用"),
    ("预测未来销量、订单量或收入", "当前只支持历史查询，不支持预测"),
    ("支付金额按商品品类拆分", "支付与订单商品均为一对多，V1禁止多事实表Fanout"),
    ("评价分数按商品品类分析", "评价与订单商品均为一对多，V1禁止多事实表Fanout"),
]

AMBIGUOUS_EXAMPLES = ["Olist经营情况", "Olist业务表现", "看看Olist数据"]


def seed() -> None:
    with SessionLocal() as session:
        domain = session.get(BusinessDomain, "sales")
        domain_values = {
            "name": "Olist电商经营",
            "description": "订单、商品、客户、卖家、支付、评价和履约分析",
            "status": "ACTIVE",
        }
        if domain is None:
            session.add(BusinessDomain(id="sales", **domain_values))
        else:
            for key, value in domain_values.items():
                setattr(domain, key, value)
        for dimension_id, name, grain in (
            ("D_DATE", "日期", "day"),
            ("D_MONTH", "月份", "month"),
        ):
            dimension = session.get(Dimension, dimension_id)
            if dimension is None:
                session.add(
                    Dimension(
                        id=dimension_id,
                        name=name,
                        dimension_type="time_grain",
                        mapping_json={},
                        allowed_operators=["eq", "neq", "gt", "gte", "lt", "lte", "between"],
                        status="ACTIVE",
                    )
                )
        session.flush()
        for model_id, (name, physical_table, default_time_field, status) in OLIST_MODELS.items():
            model = session.get(SemanticModel, model_id)
            values = {
                "business_domain_id": "sales", "name": name, "warehouse": "clickhouse",
                "physical_table": physical_table, "default_time_field": default_time_field,
                "status": status,
            }
            if model is None:
                session.add(SemanticModel(id=model_id, **values))
            else:
                for key, value in values.items():
                    setattr(model, key, value)
        session.flush()

        for entity_id, (model_id, name, grain, keys, entity_type, status) in ENTITIES.items():
            entity = session.get(SemanticEntity, entity_id)
            values = {
                "semantic_model_id": model_id, "business_domain_id": "sales", "name": name,
                "grain": grain, "primary_key_json": keys, "entity_type": entity_type,
                "status": status,
            }
            if entity is None:
                session.add(SemanticEntity(id=entity_id, **values))
            else:
                for key, value in values.items():
                    setattr(entity, key, value)
        session.flush()

        for relation_id, values_tuple in RELATIONS.items():
            left, right, left_keys, right_keys, relationship, join_type, strategy, status, priority = values_tuple
            relation = session.get(SemanticJoinRelation, relation_id)
            values = {
                "business_domain_id": "sales", "left_entity_id": left, "right_entity_id": right,
                "left_keys_json": left_keys, "right_keys_json": right_keys,
                "relationship_type": relationship, "join_type": join_type,
                "fanout_strategy": strategy, "priority": priority, "status": status, "version": 1,
            }
            if relation is None:
                session.add(SemanticJoinRelation(id=relation_id, **values))
            else:
                for key, value in values.items():
                    setattr(relation, key, value)

        base_model_id = "SM_OLIST_ORDER_ITEMS"
        for dimension_id in ("D_DATE", "D_MONTH"):
            dimension = session.get(Dimension, dimension_id)
            if dimension is None:
                raise RuntimeError(f"Base dimension does not exist: {dimension_id}")
            mapping = {
                "kind": "time_grain",
                "field": "order_purchase_timestamp",
                "grain": "day" if dimension_id == "D_DATE" else "month",
                "source_model_id": "SM_OLIST_ORDERS",
            }
            dimension.mapping_json = {**(dimension.mapping_json or {}), base_model_id: mapping}

        for dimension_id, (name, kind, source_model_id, field) in DIMENSIONS.items():
            dimension = session.get(Dimension, dimension_id)
            mapping = {"kind": "field", "field": field, "source_model_id": source_model_id}
            values = {
                "name": name, "dimension_type": kind,
                "mapping_json": {base_model_id: mapping},
                "allowed_operators": ["eq", "neq", "in", "not_in"], "status": "ACTIVE",
            }
            if dimension is None:
                session.add(Dimension(id=dimension_id, **values))
            else:
                dimension.name = name
                dimension.dimension_type = kind
                dimension.mapping_json = {**(dimension.mapping_json or {}), base_model_id: mapping}
                dimension.allowed_operators = values["allowed_operators"]
                dimension.status = "ACTIVE"
        session.flush()

        dimension_ids = ["D_DATE", "D_MONTH", *DIMENSIONS]
        for metric_id, name, description, metric_type, unit, expression, aliases, positives in METRICS:
            metric = session.get(Metric, metric_id)
            values = {
                "business_domain_id": "sales", "name": name, "description": description,
                "metric_type": metric_type, "unit": unit, "owner": "data-platform",
                "status": "PUBLISHED",
            }
            if metric is None:
                metric = Metric(id=metric_id, **values)
                session.add(metric)
            else:
                for key, value in values.items():
                    setattr(metric, key, value)
            session.flush()
            version = session.scalar(
                select(MetricVersion).where(
                    MetricVersion.metric_id == metric_id, MetricVersion.version == 1
                )
            )
            if version is None:
                session.add(
                    MetricVersion(
                        metric_id=metric_id, version=1, semantic_model_id=base_model_id,
                        expression_json=expression, default_aggregation="default",
                        time_dimension_id="D_DATE", status="PUBLISHED",
                    )
                )
            for alias in aliases:
                if session.scalar(
                    select(MetricAlias).where(
                        MetricAlias.metric_id == metric_id, MetricAlias.alias == alias
                    )
                ) is None:
                    session.add(MetricAlias(metric_id=metric_id, alias=alias))
            profile = session.get(MetricSemanticProfile, metric_id)
            profile_values = {
                "positive_examples_json": [*positives, *AMBIGUOUS_EXAMPLES], "negative_examples_json": [],
                "retrieval_config_json": {"enabled": True, "strategy": "hybrid_join_v1"},
                "updated_by": "data-platform",
            }
            if profile is None:
                session.add(MetricSemanticProfile(metric_id=metric_id, **profile_values))
            else:
                for key, value in profile_values.items():
                    setattr(profile, key, value)
            for dimension_id in dimension_ids:
                if session.get(MetricDimension, (metric_id, dimension_id)) is None:
                    session.add(MetricDimension(metric_id=metric_id, dimension_id=dimension_id))
        for existing in session.scalars(
            select(SemanticScopeExample).where(
                SemanticScopeExample.business_domain_id == "sales"
            )
        ):
            existing.is_active = False
        for text, reason in OUT_OF_SCOPE_EXAMPLES:
            digest = source_hash(text)
            example = session.scalar(
                select(SemanticScopeExample).where(
                    SemanticScopeExample.business_domain_id == "sales",
                    SemanticScopeExample.source_hash == digest,
                )
            )
            values = {
                "text": text,
                "label": "OUT_OF_SCOPE",
                "reason": reason,
                "is_active": True,
            }
            if example is None:
                session.add(
                    SemanticScopeExample(
                        business_domain_id="sales", source_hash=digest, **values
                    )
                )
            else:
                for key, value in values.items():
                    setattr(example, key, value)
        session.commit()
    print("Published 3 Olist V1 metrics on 5 safe join paths; risky entities remain STAGED")


if __name__ == "__main__":
    seed()
