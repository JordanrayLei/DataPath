TRUNCATE TABLE data_warehouse.dwd_sales_order_item;
TRUNCATE TABLE data_warehouse.dwd_ad_delivery_day;
TRUNCATE TABLE data_warehouse.dws_sales_day;
TRUNCATE TABLE data_warehouse.dws_ad_delivery_day;

INSERT INTO data_warehouse.dwd_sales_order_item
SELECT
    toDate(assumeNotNull(paid_at)) AS biz_date,
    order_id,
    order_item_id,
    user_id,
    product_id,
    product_name,
    category_id,
    category_name,
    region,
    province,
    sales_channel,
    assumeNotNull(paid_at) AS paid_at,
    quantity,
    gross_amount,
    paid_amount,
    refund_amount,
    item_cost AS recognized_item_cost,
    paid_amount - refund_amount AS net_revenue,
    paid_amount - refund_amount - item_cost AS gross_profit
FROM data_warehouse.ods_sales_order_item
WHERE
    is_test = 0
    AND order_status IN ('paid', 'partially_refunded', 'refunded')
    AND paid_at IS NOT NULL;

INSERT INTO data_warehouse.dwd_ad_delivery_day
SELECT *
FROM data_warehouse.ods_ad_delivery_day;

INSERT INTO data_warehouse.dws_sales_day
SELECT
    biz_date,
    region,
    province,
    sales_channel,
    category_id,
    any(category_name) AS category_name,
    sum(gross_amount) AS gmv,
    sum(paid_amount) AS paid_revenue,
    sum(refund_amount) AS refund_amount,
    sum(recognized_item_cost) AS recognized_item_cost,
    sum(gross_profit) AS gross_profit,
    toUInt64(sum(quantity)) AS item_quantity,
    uniqExactState(order_id) AS order_count_state
FROM data_warehouse.dwd_sales_order_item
GROUP BY
    biz_date,
    region,
    province,
    sales_channel,
    category_id;

INSERT INTO data_warehouse.dws_ad_delivery_day
SELECT
    biz_date,
    ad_platform,
    ad_account,
    campaign_id,
    any(campaign_name) AS campaign_name,
    device_type,
    attribution_window,
    sum(impressions) AS impressions,
    sum(clicks) AS clicks,
    sum(spend) AS spend,
    sum(conversions) AS conversions,
    sum(attributed_revenue) AS attributed_revenue
FROM data_warehouse.dwd_ad_delivery_day
GROUP BY
    biz_date,
    ad_platform,
    ad_account,
    campaign_id,
    device_type,
    attribution_window;
