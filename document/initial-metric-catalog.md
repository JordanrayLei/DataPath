# DataPath Olist 指标目录

> 版本：V2.0
> 更新日期：2026-07-13
> 当前已发布：12 个指标，均为 v1

## 指标表

| 指标 ID | 名称 | 公式摘要 | 单位 | 主要口径 |
| --- | --- | --- | --- | --- |
| `M_OLIST_ITEM_REVENUE` | Olist 商品销售额 | `SUM(price)` | BRL | 不含运费 |
| `M_OLIST_FREIGHT_VALUE` | Olist 运费 | `SUM(freight_value)` | BRL | 订单商品行运费 |
| `M_OLIST_ORDER_COUNT` | Olist 订单量 | `COUNT DISTINCT order_id` | order | 订单商品事实中的去重订单 |
| `M_OLIST_TOTAL_ORDER_VALUE` | Olist 成交总额 | `SUM(price) + SUM(freight_value)` | BRL | 不等同支付表实际支付金额 |
| `M_OLIST_AVERAGE_ORDER_VALUE` | Olist 客单价 | 商品销售额 / 去重订单量 | BRL/order | 不含运费 |
| `M_OLIST_FREIGHT_PER_ORDER` | Olist 平均每单运费 | 运费 / 去重订单量 | BRL/order | 零订单返回空值 |
| `M_OLIST_FREIGHT_RATE` | Olist 运费率 | 运费 / 商品销售额 x 100 | % | 零销售额返回空值 |
| `M_OLIST_ITEM_COUNT` | Olist 商品件数 | `COUNT(order_id)` | item | 一个订单商品明细行计一件 |
| `M_OLIST_ITEMS_PER_ORDER` | Olist 每单商品件数 | 商品件数 / 去重订单量 | item/order | 平均件单量 |
| `M_OLIST_PRODUCT_COUNT` | Olist 成交商品数 | `COUNT DISTINCT product_id` | product | 有成交明细的去重商品 |
| `M_OLIST_SELLER_COUNT` | Olist 活跃卖家数 | `COUNT DISTINCT seller_id` | seller | 有成交明细的去重卖家 |
| `M_OLIST_CUSTOMER_COUNT` | Olist 购买客户数 | `COUNT DISTINCT customer_unique_id` | customer | 同一客户多次下单只计一次 |

## 可用维度

当前指标统一支持日期、月份、商品品类、客户州、卖家州和订单状态。具体可用性以指标中心 `MetricDimension` 发布数据为准。

## 语义模型与 Join

当前指标以 `SM_OLIST_ORDER_ITEMS` 为基准模型，通过已发布关系连接订单、客户、商品、卖家和品类翻译。购买客户数从客户模型读取 `customer_unique_id` 并通过订单路径去重。

## 口径边界

- 不支持商品成本、毛利、退款、库存、广告、优惠券或预测指标。
- 支付金额、支付方式、评价分数尚未发布为指标。
- “成交总额”是商品价格与运费之和，不使用支付表。
- 比率和平均指标不能跨维度直接相加；结果画像不会把分组比率当加法指标汇总。

## 维护规则

指标只能通过草稿校验和版本发布进入在线检索。修改现有口径必须生成新版本，不直接覆盖已发布版本。新增指标后需重建语义索引并补充黄金问题。
