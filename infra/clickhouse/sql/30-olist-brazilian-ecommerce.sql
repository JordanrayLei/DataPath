CREATE TABLE IF NOT EXISTS data_warehouse.olist_customers
(
    customer_id String,
    customer_unique_id String,
    customer_zip_code_prefix UInt32,
    customer_city LowCardinality(String),
    customer_state LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY customer_id;

CREATE TABLE IF NOT EXISTS data_warehouse.olist_orders
(
    order_id String,
    customer_id String,
    order_status LowCardinality(String),
    order_purchase_timestamp DateTime('UTC'),
    order_approved_at Nullable(DateTime('UTC')),
    order_delivered_carrier_date Nullable(DateTime('UTC')),
    order_delivered_customer_date Nullable(DateTime('UTC')),
    order_estimated_delivery_date DateTime('UTC')
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(order_purchase_timestamp)
ORDER BY (order_purchase_timestamp, order_id);

CREATE TABLE IF NOT EXISTS data_warehouse.olist_order_items
(
    order_id String,
    order_item_id UInt16,
    product_id String,
    seller_id String,
    shipping_limit_date DateTime('UTC'),
    price Decimal(18, 2),
    freight_value Decimal(18, 2)
)
ENGINE = MergeTree
ORDER BY (order_id, order_item_id);

CREATE TABLE IF NOT EXISTS data_warehouse.olist_order_payments
(
    order_id String,
    payment_sequential UInt16,
    payment_type LowCardinality(String),
    payment_installments UInt16,
    payment_value Decimal(18, 2)
)
ENGINE = MergeTree
ORDER BY (order_id, payment_sequential);

CREATE TABLE IF NOT EXISTS data_warehouse.olist_order_reviews
(
    review_id String,
    order_id String,
    review_score UInt8,
    review_comment_title Nullable(String),
    review_comment_message Nullable(String),
    review_creation_date DateTime('UTC'),
    review_answer_timestamp DateTime('UTC')
)
ENGINE = MergeTree
ORDER BY (order_id, review_id);

CREATE TABLE IF NOT EXISTS data_warehouse.olist_products
(
    product_id String,
    product_category_name Nullable(String),
    product_name_lenght Nullable(UInt16),
    product_description_lenght Nullable(UInt16),
    product_photos_qty Nullable(UInt16),
    product_weight_g Nullable(UInt32),
    product_length_cm Nullable(UInt16),
    product_height_cm Nullable(UInt16),
    product_width_cm Nullable(UInt16)
)
ENGINE = MergeTree
ORDER BY product_id;

CREATE TABLE IF NOT EXISTS data_warehouse.olist_sellers
(
    seller_id String,
    seller_zip_code_prefix UInt32,
    seller_city LowCardinality(String),
    seller_state LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY seller_id;

CREATE TABLE IF NOT EXISTS data_warehouse.olist_geolocation
(
    geolocation_zip_code_prefix UInt32,
    geolocation_lat Float64,
    geolocation_lng Float64,
    geolocation_city String,
    geolocation_state LowCardinality(String)
)
ENGINE = MergeTree
ORDER BY (geolocation_zip_code_prefix, geolocation_city, geolocation_lat, geolocation_lng);

CREATE TABLE IF NOT EXISTS data_warehouse.olist_product_category_translation
(
    product_category_name String,
    product_category_name_english String
)
ENGINE = MergeTree
ORDER BY product_category_name;
