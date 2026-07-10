SELECT
    'M_SALES_GMV' AS metric_id,
    toString(round(sum(gross_amount), 2)) AS value,
    'CNY' AS unit
FROM data_warehouse.dwd_sales_order_item

UNION ALL

SELECT
    'M_SALES_PAID_REVENUE' AS metric_id,
    toString(round(sum(paid_amount), 2)) AS value,
    'CNY' AS unit
FROM data_warehouse.dwd_sales_order_item

UNION ALL

SELECT
    'M_SALES_ORDER_COUNT' AS metric_id,
    toString(uniqExact(order_id)) AS value,
    'order' AS unit
FROM data_warehouse.dwd_sales_order_item

UNION ALL

SELECT
    'M_SALES_GROSS_PROFIT' AS metric_id,
    toString(round(sum(gross_profit), 2)) AS value,
    'CNY' AS unit
FROM data_warehouse.dwd_sales_order_item

UNION ALL

SELECT
    'M_SALES_GROSS_MARGIN_RATE' AS metric_id,
    toString(round(if(
        sum(net_revenue) = 0,
        NULL,
        toFloat64(sum(gross_profit)) / toFloat64(sum(net_revenue)) * 100
    ), 2)) AS value,
    '%' AS unit
FROM data_warehouse.dwd_sales_order_item

UNION ALL

SELECT
    'M_AD_ROAS' AS metric_id,
    toString(round(if(
        sum(spend) = 0,
        NULL,
        toFloat64(sum(attributed_revenue)) / toFloat64(sum(spend))
    ), 2)) AS value,
    'multiple' AS unit
FROM data_warehouse.dwd_ad_delivery_day

FORMAT JSONEachRow;
