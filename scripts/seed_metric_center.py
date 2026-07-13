"""Seed the governed Olist metrics, dimensions, and semantic models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db.models import (
    BusinessDomain,
    Dimension,
    Metric,
    MetricAlias,
    MetricDimension,
    MetricVersion,
    SemanticModel,
)
from app.db.session import SessionLocal


SALES_MODEL = "SM_SALES_ORDER_ITEM"
AD_MODEL = "SM_AD_DELIVERY_DAY"
ENUM_OPERATORS = ["eq", "neq", "in", "not_in"]
TIME_OPERATORS = ["eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte", "between"]


def update_fields(instance: Any, values: dict[str, Any]) -> None:
    for key, value in values.items():
        setattr(instance, key, value)


def seed(include_legacy: bool = False) -> None:
    if not include_legacy:
        from scripts.seed_olist_staging import seed as seed_olist_metrics

        seed_olist_metrics()
        return
    with SessionLocal() as session:
        domains = [
            {
                "id": "sales",
                "name": "电商经营",
                "description": "订单、收入、退款和毛利分析",
                "status": "ACTIVE",
            },
            {
                "id": "advertising",
                "name": "广告投放",
                "description": "曝光、点击、消耗、转化和回报分析",
                "status": "ACTIVE",
            },
        ]
        for values in domains:
            row = session.get(BusinessDomain, values["id"])
            if row is None:
                session.add(BusinessDomain(**values))
            else:
                update_fields(row, values)
        session.flush()

        models = [
            {
                "id": SALES_MODEL,
                "business_domain_id": "sales",
                "name": "销售订单商品模型",
                "warehouse": "clickhouse",
                "physical_table": "data_warehouse.dwd_sales_order_item",
                "default_time_field": "biz_date",
                "status": "ACTIVE",
            },
            {
                "id": AD_MODEL,
                "business_domain_id": "advertising",
                "name": "广告投放日模型",
                "warehouse": "clickhouse",
                "physical_table": "data_warehouse.dwd_ad_delivery_day",
                "default_time_field": "biz_date",
                "status": "ACTIVE",
            },
        ]
        for values in models:
            row = session.get(SemanticModel, values["id"])
            if row is None:
                session.add(SemanticModel(**values))
            else:
                update_fields(row, values)
        session.flush()

        dimensions = [
            {
                "id": "D_DATE",
                "name": "日期",
                "dimension_type": "date",
                "mapping_json": {
                    SALES_MODEL: {"kind": "field", "field": "biz_date"},
                    AD_MODEL: {"kind": "field", "field": "biz_date"},
                },
                "allowed_operators": TIME_OPERATORS,
            },
            {
                "id": "D_MONTH",
                "name": "月",
                "dimension_type": "time_grain",
                "mapping_json": {
                    SALES_MODEL: {"kind": "time_grain", "field": "biz_date", "grain": "month"},
                    AD_MODEL: {"kind": "time_grain", "field": "biz_date", "grain": "month"},
                },
                "allowed_operators": TIME_OPERATORS,
            },
            {
                "id": "D_REGION",
                "name": "地区",
                "dimension_type": "enum",
                "mapping_json": {SALES_MODEL: {"kind": "field", "field": "region"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_PROVINCE",
                "name": "省份",
                "dimension_type": "enum",
                "mapping_json": {SALES_MODEL: {"kind": "field", "field": "province"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_SALES_CHANNEL",
                "name": "销售渠道",
                "dimension_type": "enum",
                "mapping_json": {SALES_MODEL: {"kind": "field", "field": "sales_channel"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_PRODUCT",
                "name": "商品",
                "dimension_type": "entity",
                "mapping_json": {SALES_MODEL: {"kind": "field", "field": "product_name"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_CATEGORY",
                "name": "商品品类",
                "dimension_type": "enum",
                "mapping_json": {SALES_MODEL: {"kind": "field", "field": "category_name"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_AD_PLATFORM",
                "name": "广告平台",
                "dimension_type": "enum",
                "mapping_json": {AD_MODEL: {"kind": "field", "field": "ad_platform"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_AD_ACCOUNT",
                "name": "广告账户",
                "dimension_type": "entity",
                "mapping_json": {AD_MODEL: {"kind": "field", "field": "ad_account"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_CAMPAIGN",
                "name": "广告计划",
                "dimension_type": "entity",
                "mapping_json": {AD_MODEL: {"kind": "field", "field": "campaign_name"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_DEVICE_TYPE",
                "name": "设备类型",
                "dimension_type": "enum",
                "mapping_json": {AD_MODEL: {"kind": "field", "field": "device_type"}},
                "allowed_operators": ENUM_OPERATORS,
            },
            {
                "id": "D_ATTRIBUTION_WINDOW",
                "name": "归因窗口",
                "dimension_type": "enum",
                "mapping_json": {AD_MODEL: {"kind": "field", "field": "attribution_window"}},
                "allowed_operators": ENUM_OPERATORS,
            },
        ]
        for values in dimensions:
            values = {**values, "status": "ACTIVE"}
            row = session.get(Dimension, values["id"])
            if row is None:
                session.add(Dimension(**values))
            else:
                incoming_mapping = values["mapping_json"]
                update_fields(row, {key: value for key, value in values.items() if key != "mapping_json"})
                row.mapping_json = {**(row.mapping_json or {}), **incoming_mapping}
        session.flush()

        metrics = [
            {
                "id": "M_SALES_GMV",
                "business_domain_id": "sales",
                "name": "GMV",
                "description": "成功支付订单对应的商品成交总额，不因后续退款减少。",
                "metric_type": "amount",
                "unit": "CNY",
                "model": SALES_MODEL,
                "expression": {"op": "sum", "field": "gross_amount"},
                "aliases": ["成交总额", "商品交易总额", "交易额"],
                "dimensions": ["D_DATE", "D_MONTH", "D_REGION", "D_PROVINCE", "D_SALES_CHANNEL", "D_PRODUCT", "D_CATEGORY"],
            },
            {
                "id": "M_SALES_PAID_REVENUE",
                "business_domain_id": "sales",
                "name": "已支付销售额",
                "description": "统计期内成功支付的商品金额，退款通过退款指标单独体现。",
                "metric_type": "amount",
                "unit": "CNY",
                "model": SALES_MODEL,
                "expression": {"op": "sum", "field": "paid_amount"},
                "aliases": ["销售额", "支付销售额", "支付金额", "实付销售额"],
                "dimensions": ["D_DATE", "D_MONTH", "D_REGION", "D_PROVINCE", "D_SALES_CHANNEL", "D_PRODUCT", "D_CATEGORY"],
            },
            {
                "id": "M_SALES_ORDER_COUNT",
                "business_domain_id": "sales",
                "name": "支付订单量",
                "description": "统计期内至少成功支付一次的去重订单数。",
                "metric_type": "count",
                "unit": "order",
                "model": SALES_MODEL,
                "expression": {"op": "count_distinct", "field": "order_id"},
                "aliases": ["支付订单数", "成交订单量", "订单量"],
                "dimensions": ["D_DATE", "D_MONTH", "D_REGION", "D_PROVINCE", "D_SALES_CHANNEL"],
            },
            {
                "id": "M_SALES_GROSS_PROFIT",
                "business_domain_id": "sales",
                "name": "毛利额",
                "description": "已支付销售额扣除成功退款和对应商品成本后的金额。",
                "metric_type": "amount",
                "unit": "CNY",
                "model": SALES_MODEL,
                "expression": {"op": "sum", "field": "gross_profit"},
                "aliases": ["毛利", "销售毛利", "主营毛利额"],
                "dimensions": ["D_DATE", "D_MONTH", "D_REGION", "D_PROVINCE", "D_SALES_CHANNEL", "D_PRODUCT", "D_CATEGORY"],
            },
            {
                "id": "M_SALES_GROSS_MARGIN_RATE",
                "business_domain_id": "sales",
                "name": "毛利率",
                "description": "毛利额占扣除退款后销售收入的比例。",
                "metric_type": "ratio",
                "unit": "%",
                "model": SALES_MODEL,
                "expression": {
                    "op": "ratio",
                    "numerator": {"op": "sum", "field": "gross_profit"},
                    "denominator": {"op": "sum", "field": "net_revenue"},
                    "scale": 100,
                    "zero_policy": "null",
                },
                "aliases": ["毛利", "销售毛利率", "主营业务毛利率", "毛利比例"],
                "dimensions": ["D_DATE", "D_MONTH", "D_REGION", "D_PROVINCE", "D_SALES_CHANNEL", "D_PRODUCT", "D_CATEGORY"],
            },
            {
                "id": "M_AD_ROAS",
                "business_domain_id": "advertising",
                "name": "广告支出回报",
                "description": "广告归因收入与广告消耗的倍数。",
                "metric_type": "ratio",
                "unit": "multiple",
                "model": AD_MODEL,
                "expression": {
                    "op": "ratio",
                    "numerator": {"op": "sum", "field": "attributed_revenue"},
                    "denominator": {"op": "sum", "field": "spend"},
                    "scale": 1,
                    "zero_policy": "null",
                },
                "aliases": ["ROAS", "广告回报倍数", "投产比"],
                "dimensions": ["D_DATE", "D_MONTH", "D_AD_PLATFORM", "D_AD_ACCOUNT", "D_CAMPAIGN", "D_DEVICE_TYPE", "D_ATTRIBUTION_WINDOW"],
            },
        ]

        for definition in metrics:
            metric_values = {
                key: definition[key]
                for key in (
                    "id",
                    "business_domain_id",
                    "name",
                    "description",
                    "metric_type",
                    "unit",
                )
            }
            metric_values.update(owner="data-platform", status="PUBLISHED")
            metric = session.get(Metric, definition["id"])
            if metric is None:
                metric = Metric(**metric_values)
                session.add(metric)
            else:
                update_fields(metric, metric_values)
            session.flush()

            version = session.scalar(
                select(MetricVersion).where(
                    MetricVersion.metric_id == definition["id"],
                    MetricVersion.version == 1,
                )
            )
            version_values = {
                "semantic_model_id": definition["model"],
                "expression_json": definition["expression"],
                "default_aggregation": "default",
                "time_dimension_id": "D_DATE",
                "status": "PUBLISHED",
            }
            if version is None:
                session.add(
                    MetricVersion(
                        metric_id=definition["id"],
                        version=1,
                        **version_values,
                    )
                )
            else:
                update_fields(version, version_values)

            for alias in definition["aliases"]:
                existing_alias = session.scalar(
                    select(MetricAlias).where(
                        MetricAlias.metric_id == definition["id"],
                        MetricAlias.alias == alias,
                    )
                )
                if existing_alias is None:
                    session.add(MetricAlias(metric_id=definition["id"], alias=alias))

            for dimension_id in definition["dimensions"]:
                key = (definition["id"], dimension_id)
                if session.get(MetricDimension, key) is None:
                    session.add(
                        MetricDimension(
                            metric_id=definition["id"],
                            dimension_id=dimension_id,
                        )
                    )

        session.commit()

    print("Seeded 2 domains, 2 semantic models, 12 dimensions, and 6 published metrics")


if __name__ == "__main__":
    seed()
