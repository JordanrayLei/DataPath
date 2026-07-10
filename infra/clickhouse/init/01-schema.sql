CREATE DATABASE IF NOT EXISTS data_warehouse;

CREATE TABLE IF NOT EXISTS data_warehouse.ods_sales_order_item
(
    order_id String,
    order_item_id String,
    user_id String,
    product_id String,
    product_name String,
    category_id LowCardinality(String),
    category_name LowCardinality(String),
    region LowCardinality(String),
    province LowCardinality(String),
    sales_channel LowCardinality(String),
    created_at DateTime('Asia/Shanghai'),
    paid_at Nullable(DateTime('Asia/Shanghai')),
    order_status LowCardinality(String),
    quantity UInt16,
    unit_price Decimal(18, 2),
    gross_amount Decimal(18, 2),
    paid_amount Decimal(18, 2),
    refund_amount Decimal(18, 2),
    item_cost Decimal(18, 2),
    is_test UInt8
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (created_at, order_id, order_item_id);

CREATE TABLE IF NOT EXISTS data_warehouse.ods_ad_delivery_day
(
    biz_date Date,
    ad_platform LowCardinality(String),
    ad_account String,
    campaign_id String,
    campaign_name String,
    creative_id String,
    device_type LowCardinality(String),
    attribution_window LowCardinality(String),
    impressions UInt64,
    clicks UInt64,
    spend Decimal(18, 2),
    conversions UInt64,
    attributed_revenue Decimal(18, 2)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(biz_date)
ORDER BY (biz_date, ad_platform, campaign_id, creative_id, device_type);

CREATE TABLE IF NOT EXISTS data_warehouse.dwd_sales_order_item
(
    biz_date Date,
    order_id String,
    order_item_id String,
    user_id String,
    product_id String,
    product_name String,
    category_id LowCardinality(String),
    category_name LowCardinality(String),
    region LowCardinality(String),
    province LowCardinality(String),
    sales_channel LowCardinality(String),
    paid_at DateTime('Asia/Shanghai'),
    quantity UInt16,
    gross_amount Decimal(18, 2),
    paid_amount Decimal(18, 2),
    refund_amount Decimal(18, 2),
    recognized_item_cost Decimal(18, 2),
    net_revenue Decimal(18, 2),
    gross_profit Decimal(18, 2)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(biz_date)
ORDER BY (biz_date, sales_channel, region, category_id, order_id, order_item_id);

CREATE TABLE IF NOT EXISTS data_warehouse.dwd_ad_delivery_day
(
    biz_date Date,
    ad_platform LowCardinality(String),
    ad_account String,
    campaign_id String,
    campaign_name String,
    creative_id String,
    device_type LowCardinality(String),
    attribution_window LowCardinality(String),
    impressions UInt64,
    clicks UInt64,
    spend Decimal(18, 2),
    conversions UInt64,
    attributed_revenue Decimal(18, 2)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(biz_date)
ORDER BY (biz_date, ad_platform, campaign_id, creative_id, device_type);

CREATE TABLE IF NOT EXISTS data_warehouse.dws_sales_day
(
    biz_date Date,
    region LowCardinality(String),
    province LowCardinality(String),
    sales_channel LowCardinality(String),
    category_id LowCardinality(String),
    category_name LowCardinality(String),
    gmv Decimal(20, 2),
    paid_revenue Decimal(20, 2),
    refund_amount Decimal(20, 2),
    recognized_item_cost Decimal(20, 2),
    gross_profit Decimal(20, 2),
    item_quantity UInt64,
    order_count_state AggregateFunction(uniqExact, String)
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(biz_date)
ORDER BY (biz_date, region, province, sales_channel, category_id);

CREATE TABLE IF NOT EXISTS data_warehouse.dws_ad_delivery_day
(
    biz_date Date,
    ad_platform LowCardinality(String),
    ad_account String,
    campaign_id String,
    campaign_name String,
    device_type LowCardinality(String),
    attribution_window LowCardinality(String),
    impressions UInt64,
    clicks UInt64,
    spend Decimal(20, 2),
    conversions UInt64,
    attributed_revenue Decimal(20, 2)
)
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(biz_date)
ORDER BY (biz_date, ad_platform, ad_account, campaign_id, device_type, attribution_window);

CREATE USER IF NOT EXISTS chatbi_reader
IDENTIFIED WITH sha256_password BY 'chatbi_reader_dev';

GRANT SELECT ON data_warehouse.* TO chatbi_reader;

