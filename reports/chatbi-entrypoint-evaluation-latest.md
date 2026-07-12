# ChatBI 产品入口测评报告

> 生成时间：2026-07-12T14:02:03.558112+00:00
> 目标：`in-process TestClient`

## 结论

- 总体状态：`PASS`
- 总通过：36/36，通过率：100.00%
- 用例通过：30/30
- 安全/可信门禁通过：6/6
- 平均响应时间：309.63ms
- P95响应时间：1406ms

## 分层结果

| 类型 | 通过 | 总数 | 通过率 |
| --- | ---: | ---: | ---: |
| olist_success | 18 | 18 | 100.00% |
| ambiguity | 3 | 3 | 100.00% |
| scope_boundary | 6 | 6 | 100.00% |
| permission | 3 | 3 | 100.00% |

## 用例明细

| 用例 | 结果 | 问题 | 状态 | 指标 | 意图 | 图表 | 行数 | Evidence | Reflection | 耗时 |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |
| revenue_total_2017 | PASS | 2017年Olist销售额 | SUCCESS | M_OLIST_ITEM_REVENUE | aggregate_query | metric | 1 | 1 | PASS | 102ms |
| revenue_month_2017 | PASS | 2017年每月Olist销售额趋势 | SUCCESS | M_OLIST_ITEM_REVENUE | trend_query | line | 12 | 3 | PASS | 36ms |
| revenue_category | PASS | 2017年各商品品类Olist销售额排名 | SUCCESS | M_OLIST_ITEM_REVENUE | ranking_query | bar | 72 | 6 | PASS | 95ms |
| revenue_customer_state | PASS | 2017年各客户州Olist销售额 | SUCCESS | M_OLIST_ITEM_REVENUE | aggregate_query | bar | 27 | 6 | PASS | 96ms |
| revenue_seller_state | PASS | 2017年各卖家州Olist销售额 | SUCCESS | M_OLIST_ITEM_REVENUE | aggregate_query | bar | 20 | 6 | PASS | 52ms |
| revenue_status | PASS | 2017年各订单状态Olist销售额 | SUCCESS | M_OLIST_ITEM_REVENUE | aggregate_query | bar | 6 | 6 | PASS | 69ms |
| freight_total_2017 | PASS | 2017年Olist运费 | SUCCESS | M_OLIST_FREIGHT_VALUE | aggregate_query | metric | 1 | 1 | PASS | 54ms |
| freight_month_2017 | PASS | 2017年每月Olist物流费趋势 | SUCCESS | M_OLIST_FREIGHT_VALUE | trend_query | line | 12 | 3 | PASS | 58ms |
| freight_category | PASS | 2017年各品类Olist配送费 | SUCCESS | M_OLIST_FREIGHT_VALUE | aggregate_query | bar | 72 | 6 | PASS | 59ms |
| freight_seller_state | PASS | 2017年各卖家州Olist运费排名 | SUCCESS | M_OLIST_FREIGHT_VALUE | ranking_query | bar | 20 | 6 | PASS | 40ms |
| orders_total_2017 | PASS | 2017年Olist订单量 | SUCCESS | M_OLIST_ORDER_COUNT | aggregate_query | metric | 1 | 1 | PASS | 39ms |
| orders_month_2017 | PASS | 2017年每月Olist订单数趋势 | SUCCESS | M_OLIST_ORDER_COUNT | trend_query | line | 12 | 3 | PASS | 51ms |
| orders_category | PASS | 2017年各商品品类Olist订单量 | SUCCESS | M_OLIST_ORDER_COUNT | aggregate_query | bar | 72 | 6 | PASS | 63ms |
| orders_customer_state | PASS | 2017年各客户州Olist订单量排名 | SUCCESS | M_OLIST_ORDER_COUNT | ranking_query | bar | 27 | 6 | PASS | 45ms |
| orders_seller_state | PASS | 2017年各卖家州Olist订单量 | SUCCESS | M_OLIST_ORDER_COUNT | aggregate_query | bar | 20 | 6 | PASS | 40ms |
| orders_status | PASS | 2017年各订单状态Olist订单数 | SUCCESS | M_OLIST_ORDER_COUNT | aggregate_query | bar | 6 | 6 | PASS | 38ms |
| revenue_recent_three_months | PASS | 最近三个月Olist销售额 | SUCCESS | M_OLIST_ITEM_REVENUE | aggregate_query | metric | 1 | 1 | PASS | 30ms |
| orders_recent_year | PASS | 最近一年Olist订单量 | SUCCESS | M_OLIST_ORDER_COUNT | aggregate_query | metric | 1 | 1 | PASS | 41ms |
| clarify_1 | PASS | Olist经营情况 | CLARIFY |  |  |  |  |  |  | 6ms |
| clarify_2 | PASS | Olist业务表现 | CLARIFY |  |  |  |  |  |  | 5ms |
| clarify_3 | PASS | 看看Olist数据 | CLARIFY |  |  |  |  |  |  | 6ms |
| reject_1 | PASS | 商品成本、毛利额或毛利率是多少 | REJECT |  |  |  |  |  |  | 1407ms |
| reject_2 | PASS | 广告曝光、点击、投放费用或广告投产比 | REJECT |  |  |  |  |  |  | 1200ms |
| reject_3 | PASS | 库存余额或库存周转天数 | REJECT |  |  |  |  |  |  | 1110ms |
| reject_4 | PASS | 客户年龄、性别或其他人口属性 | REJECT |  |  |  |  |  |  | 1017ms |
| reject_5 | PASS | 预测未来销量、订单量或收入 | REJECT |  |  |  |  |  |  | 1406ms |
| reject_6 | PASS | 支付金额按商品品类拆分 | REJECT |  |  |  |  |  |  | 2106ms |
| blocked_workspace_1 | PASS | 2017年Olist销售额 | BLOCKED |  |  |  |  |  |  | 6ms |
| blocked_workspace_2 | PASS | 2017年Olist订单量 | BLOCKED |  |  |  |  |  |  | 6ms |
| blocked_workspace_3 | PASS | 2017年Olist运费 | BLOCKED |  |  |  |  |  |  | 6ms |

## 安全与可信门禁

- `internal_service_token_guard`：PASS。Internal endpoint rejected browser-style unauthenticated request.
- `metric_catalog_detail`：PASS。Metric catalog listed M_OLIST_ITEM_REVENUE with formula, dimensions, and warehouse lineage.
- `multiturn_context_inheritance`：PASS。Metric, dimension, and time context were inherited and explicitly overridden across five turns.
- `badcase_feedback_submission`：PASS。Feedback accepted as regression candidate for query_id=Q20260712140153CB9323FAFE.
- `badcase_board_lifecycle`：PASS。Feedback fb_affe323acdcf4b36b8a51d94 was listed and moved to CONFIRMED.
- `golden_question_regression`：PASS。Golden question gq_0f6766d9628548bd9d7fb49e was created and passed regression evaluation.

## 失败项

无。

## 覆盖范围

- 成功链路：自然语言到可信解读闭环。
- 排行链路：非时间维度聚合与柱状图展示。
- 歧义链路：指标口径不清时安全澄清，不执行查询。
- 拒绝链路：未知指标不生成 DSL、不编译查询。
- 权限链路：非 demo workspace 被拦截。
- 安全门禁：内部服务接口仍要求 Bearer Token。
- 指标口径门禁：指标目录能返回口径、公式、维度和数仓血缘。
- 反馈门禁：成功查询可提交 Badcase 反馈，并进入回归集候选。
- 看板门禁：Badcase 能在看板出现，并推进到 CONFIRMED 状态。
- 黄金集门禁：已确认 Badcase 能沉淀为黄金问题，并通过回归评测。
