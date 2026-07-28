"""Governed semantic constants for the production-like benchmark warehouse."""

from __future__ import annotations


DOMAIN_ID = "production_benchmark"
TABLE_PREFIX = "production_benchmark."

MODEL_TABLES = {
    "SM_PROD_ORDERS": "production_benchmark.fct_orders",
    "SM_PROD_ORDER_ITEMS": "production_benchmark.fct_order_items",
    "SM_PROD_PAYMENTS": "production_benchmark.fct_payments",
    "SM_PROD_REFUNDS": "production_benchmark.fct_refunds",
    "SM_PROD_SHIPMENTS": "production_benchmark.fct_shipments",
    "SM_PROD_INVENTORY": "production_benchmark.fct_inventory_snapshot",
    "SM_PROD_SERVICE_TICKETS": "production_benchmark.fct_service_tickets",
    "SM_PROD_MARKETING_TOUCH": "production_benchmark.fct_marketing_touch",
    "SM_PROD_CUSTOMER_SCD2": "production_benchmark.dim_customer_scd2",
    "SM_PROD_PRODUCT_SCD2": "production_benchmark.dim_product_scd2",
    "SM_PROD_WAREHOUSE": "production_benchmark.dim_warehouse",
}

FACT_MODEL_IDS = {
    "SM_PROD_ORDERS",
    "SM_PROD_ORDER_ITEMS",
    "SM_PROD_PAYMENTS",
    "SM_PROD_REFUNDS",
    "SM_PROD_SHIPMENTS",
    "SM_PROD_INVENTORY",
    "SM_PROD_SERVICE_TICKETS",
    "SM_PROD_MARKETING_TOUCH",
}

MODEL_FIELDS = {
    "SM_PROD_ORDERS": set("order_id customer_sk tenant_id order_date purchase_ts business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code timezone source_system".split()),
    "SM_PROD_ORDER_ITEMS": set("order_item_id order_id product_sk seller_sk tenant_id business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code timezone source_system source_version is_deleted".split()),
    "SM_PROD_PAYMENTS": set("payment_id order_id customer_sk tenant_id payment_ts business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code timezone".split()),
    "SM_PROD_REFUNDS": set("refund_id payment_id order_id tenant_id refund_ts business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code".split()),
    "SM_PROD_SHIPMENTS": set("shipment_id order_id warehouse_sk carrier_sk tenant_id business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code timezone source_system source_version".split()),
    "SM_PROD_INVENTORY": set("snapshot_id product_sk warehouse_sk tenant_id snapshot_date business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code".split()),
    "SM_PROD_SERVICE_TICKETS": set("ticket_id order_id customer_sk employee_sk tenant_id business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code timezone".split()),
    "SM_PROD_MARKETING_TOUCH": set("touch_id customer_sk campaign_sk channel_sk tenant_id business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount".split()),
    "SM_PROD_CUSTOMER_SCD2": set("customer_sk customer_id tenant_id valid_from valid_to is_current business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount".split()),
    "SM_PROD_PRODUCT_SCD2": set("product_sk product_id tenant_id valid_from valid_to is_current business_date event_ts currency_code status_code quantity gross_amount discount_amount net_amount region_code".split()),
    "SM_PROD_WAREHOUSE": set("warehouse_sk warehouse_id tenant_id business_date event_ts currency_code status_code quantity gross_amount discount_amount".split()),
}

DEFAULT_TIME_FIELDS = {
    "SM_PROD_ORDERS": "purchase_ts",
    "SM_PROD_ORDER_ITEMS": "event_ts",
    "SM_PROD_PAYMENTS": "payment_ts",
    "SM_PROD_REFUNDS": "refund_ts",
    "SM_PROD_SHIPMENTS": "event_ts",
    "SM_PROD_INVENTORY": "snapshot_date",
    "SM_PROD_SERVICE_TICKETS": "event_ts",
    "SM_PROD_MARKETING_TOUCH": "event_ts",
    "SM_PROD_CUSTOMER_SCD2": "valid_from",
    "SM_PROD_PRODUCT_SCD2": "valid_from",
    "SM_PROD_WAREHOUSE": "",
}

MODEL_NAMES = {
    "SM_PROD_ORDERS": "订单事实",
    "SM_PROD_ORDER_ITEMS": "订单商品事实",
    "SM_PROD_PAYMENTS": "支付事实",
    "SM_PROD_REFUNDS": "退款事实",
    "SM_PROD_SHIPMENTS": "履约包裹事实",
    "SM_PROD_INVENTORY": "库存快照事实",
    "SM_PROD_SERVICE_TICKETS": "客服工单事实",
    "SM_PROD_MARKETING_TOUCH": "营销触点事实",
    "SM_PROD_CUSTOMER_SCD2": "客户历史维度",
    "SM_PROD_PRODUCT_SCD2": "商品历史维度",
    "SM_PROD_WAREHOUSE": "仓库维度",
}

ENTITY_KEYS = {
    "SM_PROD_ORDERS": ["order_id"],
    "SM_PROD_ORDER_ITEMS": ["order_item_id"],
    "SM_PROD_PAYMENTS": ["payment_id"],
    "SM_PROD_REFUNDS": ["refund_id"],
    "SM_PROD_SHIPMENTS": ["shipment_id"],
    "SM_PROD_INVENTORY": ["snapshot_id"],
    "SM_PROD_SERVICE_TICKETS": ["ticket_id"],
    "SM_PROD_MARKETING_TOUCH": ["touch_id"],
    "SM_PROD_CUSTOMER_SCD2": ["customer_sk"],
    "SM_PROD_PRODUCT_SCD2": ["product_sk"],
    "SM_PROD_WAREHOUSE": ["warehouse_sk"],
}

RELATIONS = {
    "J_PROD_ITEMS_ORDERS": ("SM_PROD_ORDER_ITEMS", "SM_PROD_ORDERS", ["order_id"], ["order_id"], "many_to_one", "safe", "PUBLISHED"),
    "J_PROD_PAYMENTS_ORDERS": ("SM_PROD_PAYMENTS", "SM_PROD_ORDERS", ["order_id"], ["order_id"], "many_to_one", "safe", "PUBLISHED"),
    "J_PROD_REFUNDS_PAYMENTS": ("SM_PROD_REFUNDS", "SM_PROD_PAYMENTS", ["payment_id"], ["payment_id"], "many_to_one", "safe", "PUBLISHED"),
    "J_PROD_SHIPMENTS_ORDERS": ("SM_PROD_SHIPMENTS", "SM_PROD_ORDERS", ["order_id"], ["order_id"], "many_to_one", "safe", "PUBLISHED"),
    "J_PROD_TICKETS_ORDERS": ("SM_PROD_SERVICE_TICKETS", "SM_PROD_ORDERS", ["order_id"], ["order_id"], "many_to_one", "safe", "PUBLISHED"),
    "J_PROD_SHIPMENTS_WAREHOUSE": ("SM_PROD_SHIPMENTS", "SM_PROD_WAREHOUSE", ["warehouse_sk"], ["warehouse_sk"], "many_to_one", "safe", "PUBLISHED"),
    "J_PROD_ORDERS_CUSTOMER_SCD2": ("SM_PROD_ORDERS", "SM_PROD_CUSTOMER_SCD2", ["customer_sk"], ["customer_sk"], "many_to_one", "as_of_scd2", "STAGED"),
    "J_PROD_ITEMS_PRODUCT_SCD2": ("SM_PROD_ORDER_ITEMS", "SM_PROD_PRODUCT_SCD2", ["product_sk"], ["product_sk"], "many_to_one", "as_of_scd2", "STAGED"),
    "J_PROD_INVENTORY_PRODUCT_SCD2": ("SM_PROD_INVENTORY", "SM_PROD_PRODUCT_SCD2", ["product_sk"], ["product_sk"], "many_to_one", "as_of_scd2", "STAGED"),
    "J_PROD_MARKETING_CUSTOMER_SCD2": ("SM_PROD_MARKETING_TOUCH", "SM_PROD_CUSTOMER_SCD2", ["customer_sk"], ["customer_sk"], "many_to_one", "as_of_scd2", "STAGED"),
}

PUBLISHED_METRICS = [
    ("M_PROD_ORDER_COUNT", "订单量", "SM_PROD_ORDERS", "count", "order", {"op": "count_distinct", "field": "order_id"}, []),
    ("M_PROD_ORDER_GROSS_AMOUNT", "订单原始金额", "SM_PROD_ORDERS", "amount", "CNY", {"op": "sum", "field": "gross_amount"}, []),
    ("M_PROD_ITEM_NET_REVENUE", "商品净收入", "SM_PROD_ORDER_ITEMS", "amount", "CNY", {"op": "sum", "field": "net_amount"}, []),
    ("M_PROD_PAYMENT_AMOUNT", "支付实收金额", "SM_PROD_PAYMENTS", "amount", "CNY", {"op": "sum", "field": "net_amount"}, []),
    ("M_PROD_REFUND_AMOUNT", "退款金额", "SM_PROD_REFUNDS", "amount", "CNY", {"op": "sum", "field": "net_amount"}, []),
    ("M_PROD_SHIPMENT_COUNT", "发货包裹量", "SM_PROD_SHIPMENTS", "count", "shipment", {"op": "count_distinct", "field": "shipment_id"}, []),
    ("M_PROD_INVENTORY_UNITS", "库存件数", "SM_PROD_INVENTORY", "count", "item", {"op": "sum", "field": "quantity"}, []),
    ("M_PROD_SERVICE_TICKET_COUNT", "客服工单量", "SM_PROD_SERVICE_TICKETS", "count", "ticket", {"op": "count_distinct", "field": "ticket_id"}, []),
    ("M_PROD_MARKETING_TOUCH_COUNT", "营销触点量", "SM_PROD_MARKETING_TOUCH", "count", "touch", {"op": "count_distinct", "field": "touch_id"}, []),
]

METRIC_DESCRIPTIONS = {
    "M_PROD_ORDER_COUNT": "去重统计订单事实中的订单编号；一张订单只计一次，不按商品行、支付记录或包裹重复计数。",
    "M_PROD_ORDER_GROSS_AMOUNT": "汇总订单事实中的下单原始金额，口径发生在订单粒度；不扣减折扣、退款，也不代表实际到账金额。",
    "M_PROD_ITEM_NET_REVENUE": "汇总订单商品事实中扣除商品行折扣后的净额；不扣减后续退款，不使用订单头金额或支付到账金额。",
    "M_PROD_PAYMENT_AMOUNT": "汇总支付事实中每笔支付记录的净到账金额；不等同于下单金额，且不自动扣除退款事实中的退款金额。",
    "M_PROD_REFUND_AMOUNT": "汇总退款事实中已经记录的退款净额；按退款发生时间统计，不把取消订单金额或订单折扣计入退款。",
    "M_PROD_SHIPMENT_COUNT": "去重统计履约事实中的包裹编号；一个订单拆成多个包裹时分别计数，不按订单编号去重。",
    "M_PROD_INVENTORY_UNITS": "汇总库存快照事实中的库存数量；结果代表所选快照和维度范围内的件数，不代表商品种类数。",
    "M_PROD_SERVICE_TICKET_COUNT": "去重统计客服工单事实中的工单编号；同一订单可产生多个工单，每个独立工单分别计数。",
    "M_PROD_MARKETING_TOUCH_COUNT": "去重统计营销触点事实中的触点编号；每次独立触达计一次，不等同于去重客户数、活动数或转化数。",
}

STAGED_METRICS = [
    (
        "M_PROD_REFUND_ADJUSTED_REVENUE",
        "退款后净收入",
        "SM_PROD_ORDER_ITEMS",
        {
            "op": "subtract",
            "left": {"op": "sum", "field": "net_amount"},
            "right": {
                "op": "sum",
                "field": "net_amount",
                "source_model_id": "SM_PROD_REFUNDS",
            },
        },
        "需要跨事实 Aggregate-Before-Join，当前编译器未启用",
    ),
    (
        "M_PROD_PAYMENT_REFUND_RATE",
        "支付退款率",
        "SM_PROD_PAYMENTS",
        {
            "op": "ratio",
            "numerator": {
                "op": "sum",
                "field": "net_amount",
                "source_model_id": "SM_PROD_REFUNDS",
            },
            "denominator": {"op": "sum", "field": "net_amount"},
            "scale": 100,
        },
        "支付与退款粒度不同，必须先聚合再连接",
    ),
]

CROSS_FACT_METRICS = {spec[0] for spec in STAGED_METRICS}
