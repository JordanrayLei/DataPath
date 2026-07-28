CREATE DATABASE IF NOT EXISTS production_benchmark;

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_orders` (
    `order_id` UInt64,
    `customer_sk` UInt64,
    `tenant_id` UInt64,
    `order_date` Date,
    `purchase_ts` DateTime64(3),
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String),
    `timezone` LowCardinality(String),
    `source_system` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`order_id`, `customer_sk`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_order_items` (
    `order_item_id` UInt64,
    `order_id` UInt64,
    `product_sk` UInt64,
    `seller_sk` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String),
    `timezone` LowCardinality(String),
    `source_system` LowCardinality(String),
    `source_version` LowCardinality(String),
    `is_deleted` UInt8
) ENGINE = MergeTree ORDER BY (`order_item_id`, `order_id`, `product_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_payments` (
    `payment_id` UInt64,
    `order_id` UInt64,
    `customer_sk` UInt64,
    `tenant_id` UInt64,
    `payment_ts` DateTime64(3),
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String),
    `timezone` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`payment_id`, `order_id`, `customer_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_refunds` (
    `refund_id` UInt64,
    `payment_id` UInt64,
    `order_id` UInt64,
    `tenant_id` UInt64,
    `refund_ts` DateTime64(3),
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`refund_id`, `payment_id`, `order_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_shipments` (
    `shipment_id` UInt64,
    `order_id` UInt64,
    `warehouse_sk` UInt64,
    `carrier_sk` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String),
    `timezone` LowCardinality(String),
    `source_system` LowCardinality(String),
    `source_version` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`shipment_id`, `order_id`, `warehouse_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_inventory_snapshot` (
    `snapshot_id` UInt64,
    `product_sk` UInt64,
    `warehouse_sk` UInt64,
    `tenant_id` UInt64,
    `snapshot_date` Date,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`snapshot_id`, `product_sk`, `warehouse_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_service_tickets` (
    `ticket_id` UInt64,
    `order_id` UInt64,
    `customer_sk` UInt64,
    `employee_sk` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String),
    `timezone` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`ticket_id`, `order_id`, `customer_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`fct_marketing_touch` (
    `touch_id` UInt64,
    `customer_sk` UInt64,
    `campaign_sk` UInt64,
    `channel_sk` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64
) ENGINE = MergeTree ORDER BY (`touch_id`, `customer_sk`, `campaign_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_customer_scd2` (
    `customer_sk` UInt64,
    `customer_id` UInt64,
    `tenant_id` UInt64,
    `valid_from` Date,
    `valid_to` Date,
    `is_current` UInt8,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64
) ENGINE = MergeTree ORDER BY (`customer_sk`, `customer_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_product_scd2` (
    `product_sk` UInt64,
    `product_id` UInt64,
    `tenant_id` UInt64,
    `valid_from` Date,
    `valid_to` Date,
    `is_current` UInt8,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`product_sk`, `product_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_seller_scd2` (
    `seller_sk` UInt64,
    `seller_id` UInt64,
    `tenant_id` UInt64,
    `valid_from` Date,
    `valid_to` Date,
    `is_current` UInt8,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64
) ENGINE = MergeTree ORDER BY (`seller_sk`, `seller_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_date` (
    `date_sk` UInt64,
    `date_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String),
    `timezone` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`date_sk`, `date_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_time` (
    `time_sk` UInt64,
    `time_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32
) ENGINE = MergeTree ORDER BY (`time_sk`, `time_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_geography` (
    `geography_sk` UInt64,
    `geography_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`geography_sk`, `geography_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_currency_rate` (
    `currency_rate_sk` UInt64,
    `currency_rate_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64
) ENGINE = MergeTree ORDER BY (`currency_rate_sk`, `currency_rate_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_payment_method` (
    `payment_method_sk` UInt64,
    `payment_method_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`payment_method_sk`, `payment_method_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_refund_reason` (
    `refund_reason_sk` UInt64,
    `refund_reason_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`refund_reason_sk`, `refund_reason_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_warehouse` (
    `warehouse_sk` UInt64,
    `warehouse_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64
) ENGINE = MergeTree ORDER BY (`warehouse_sk`, `warehouse_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_carrier` (
    `carrier_sk` UInt64,
    `carrier_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64
) ENGINE = MergeTree ORDER BY (`carrier_sk`, `carrier_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_service_category` (
    `service_category_sk` UInt64,
    `service_category_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`service_category_sk`, `service_category_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_channel` (
    `channel_sk` UInt64,
    `channel_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`channel_sk`, `channel_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_campaign` (
    `campaign_sk` UInt64,
    `campaign_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64
) ENGINE = MergeTree ORDER BY (`campaign_sk`, `campaign_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_promotion` (
    `promotion_sk` UInt64,
    `promotion_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`promotion_sk`, `promotion_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_device` (
    `device_sk` UInt64,
    `device_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`device_sk`, `device_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_order_status` (
    `order_status_sk` UInt64,
    `order_status_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`order_status_sk`, `order_status_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_tenant` (
    `tenant_sk` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64
) ENGINE = MergeTree ORDER BY (`tenant_sk`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_employee` (
    `employee_sk` UInt64,
    `employee_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64
) ENGINE = MergeTree ORDER BY (`employee_sk`, `employee_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_risk_rule` (
    `risk_rule_sk` UInt64,
    `risk_rule_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64
) ENGINE = MergeTree ORDER BY (`risk_rule_sk`, `risk_rule_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_customer_segment` (
    `customer_segment_sk` UInt64,
    `customer_segment_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`customer_segment_sk`, `customer_segment_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`dim_product_category` (
    `product_category_sk` UInt64,
    `product_category_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32
) ENGINE = MergeTree ORDER BY (`product_category_sk`, `product_category_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`bridge_order_promotion` (
    `order_id` UInt64,
    `promotion_sk` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`order_id`, `promotion_sk`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`bridge_product_category` (
    `product_sk` UInt64,
    `category_sk` UInt64,
    `valid_from` Date,
    `valid_to` Date,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`product_sk`, `category_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`bridge_customer_segment` (
    `customer_sk` UInt64,
    `segment_sk` UInt64,
    `valid_from` Date,
    `valid_to` Date,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`customer_sk`, `segment_sk`);

CREATE TABLE IF NOT EXISTS production_benchmark.`bridge_shipment_item` (
    `shipment_id` UInt64,
    `order_item_id` UInt64,
    `tenant_id` UInt64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`shipment_id`, `order_item_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`agg_daily_sales` (
    `tenant_id` UInt64,
    `period_date` Date,
    `metric_value` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`agg_weekly_fulfillment` (
    `tenant_id` UInt64,
    `period_date` Date,
    `metric_value` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String),
    `timezone` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`agg_monthly_customer_value` (
    `tenant_id` UInt64,
    `period_date` Date,
    `metric_value` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64
) ENGINE = MergeTree ORDER BY (`tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`raw_orders` (
    `record_id` UInt64,
    `tenant_id` UInt64,
    `amount` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64,
    `net_amount` Float64,
    `region_code` LowCardinality(String)
) ENGINE = MergeTree ORDER BY (`record_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`legacy_order_summary` (
    `record_id` UInt64,
    `tenant_id` UInt64,
    `amount` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64
) ENGINE = MergeTree ORDER BY (`record_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`tmp_sales_amount` (
    `record_id` UInt64,
    `tenant_id` UInt64,
    `amount` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32
) ENGINE = MergeTree ORDER BY (`record_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`finance_amount_snapshot` (
    `record_id` UInt64,
    `tenant_id` UInt64,
    `amount` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64,
    `discount_amount` Float64
) ENGINE = MergeTree ORDER BY (`record_id`, `tenant_id`);

CREATE TABLE IF NOT EXISTS production_benchmark.`archived_customer` (
    `record_id` UInt64,
    `tenant_id` UInt64,
    `amount` Float64,
    `business_date` Date,
    `event_ts` DateTime64(3),
    `currency_code` LowCardinality(String),
    `status_code` LowCardinality(String),
    `quantity` UInt32,
    `gross_amount` Float64
) ENGINE = MergeTree ORDER BY (`record_id`, `tenant_id`);
