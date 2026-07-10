# ChatBI 产品入口测评报告

> 生成时间：2026-07-10T02:34:35.251544+00:00
> 目标：`http://127.0.0.1:8010`

## 结论

- 总体状态：`PASS`
- 总通过：10/10，通过率：100.00%
- 用例通过：5/5
- 安全/可信门禁通过：5/5

## 用例明细

| 用例 | 结果 | 问题 | 状态 | 指标 | 意图 | 图表 | 行数 | Evidence | Reflection | 耗时 |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |
| sales_monthly_gmv | PASS | 最近一年每月 GMV 趋势如何？ | SUCCESS | M_SALES_GMV | trend_query | line | 12 | 3 | PASS | 909ms |
| sales_region_ranking | PASS | 各地区 GMV 排名 | SUCCESS | M_SALES_GMV | ranking_query | bar | 4 | 5 | PASS | 237ms |
| ambiguous_gross_profit | PASS | 看看毛利 | CLARIFY |  |  |  |  |  |  | 69ms |
| unknown_metric_reject | PASS | 最近一年每月火星销售指数 | REJECT |  |  |  |  |  |  | 72ms |
| workspace_guard | PASS | 最近一年每月 GMV 趋势如何？ | BLOCKED |  |  |  |  |  |  | 62ms |

## 安全与可信门禁

- `internal_service_token_guard`：PASS。Internal endpoint rejected browser-style unauthenticated request.
- `metric_catalog_detail`：PASS。Metric catalog listed M_SALES_GMV with formula, dimensions, and warehouse lineage.
- `badcase_feedback_submission`：PASS。Feedback accepted as regression candidate for query_id=Q2026071002343237B48C2416.
- `badcase_board_lifecycle`：PASS。Feedback fb_78bd634334034dc191576afc was listed and moved to CONFIRMED.
- `golden_question_regression`：PASS。Golden question gq_5b167bbf9c734fdba9a624f4 was created and passed regression evaluation.

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
