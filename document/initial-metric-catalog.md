# AI 数据运营平台首发指标目录

> 版本：v1.0
>
> 目标：为电商经营域和广告投放域提供首批 24 个可执行指标定义。
>
> 状态：产品与数据契约草案，需在语义模型和演示数据表确定后落库。

## 1. 统一约定

### 1.1 指标状态

```text
DRAFT → VALIDATED → PUBLISHED → DEPRECATED
```

只有 `PUBLISHED` 指标进入普通用户目录、指标检索和 Dify Prompt。

### 1.2 时间与币种

- 默认时区：`Asia/Shanghai`。
- 默认币种：`CNY`。
- 金额统一保存为最小货币单位或 Decimal，不使用二进制浮点累计。
- 日期区间使用左闭右闭的业务日期表达；Compiler 转换为物理时间条件。
- 首版最大默认查询跨度为 366 天。

### 1.3 聚合规则

- 可加指标：按目标粒度直接 `SUM`。
- 去重指标：在目标粒度 `COUNT DISTINCT`。
- 比率指标：先分别聚合分子和分母，再做除法。
- 分母为 0 时返回 `null`，不返回 0 或无穷大。
- 去重和比率指标不允许客户端任意覆盖默认聚合。

## 2. 语义模型

| 模型 ID | 名称 | 业务域 | 粒度 | 主时间字段 | 事实来源 |
| --- | --- | --- | --- | --- | --- |
| `SM_SALES_ORDER_ITEM` | 销售订单明细模型 | `sales` | 一行一个订单商品 | `paid_at` | 订单、订单明细、支付、商品成本 |
| `SM_SALES_ORDER` | 销售订单模型 | `sales` | 一行一个订单 | `created_at` / `paid_at` | 订单、支付、退款 |
| `SM_SALES_BUYER_DAY` | 购买用户日模型 | `sales` | 用户 × 日期 | `biz_date` | 支付订单、用户首购日期 |
| `SM_AD_DELIVERY_DAY` | 广告投放日模型 | `advertising` | 日期 × 平台 × 计划 × 素材 | `biz_date` | 曝光、点击、消耗、转化 |
| `SM_AD_ATTRIBUTION` | 广告归因模型 | `advertising` | 一次归因转化 | `converted_at` | 广告点击、转化、归因订单 |

## 3. 公共维度

| 维度 ID | 名称 | 类型 | 示例 | 适用域 |
| --- | --- | --- | --- | --- |
| `D_DATE` | 日期 | date | `2026-07-07` | 全部 |
| `D_WEEK` | 周 | time-grain | `2026-W28` | 全部 |
| `D_MONTH` | 月 | time-grain | `2026-07` | 全部 |
| `D_QUARTER` | 季度 | time-grain | `2026-Q3` | 全部 |
| `D_REGION` | 地区 | enum | 华东、华南 | sales |
| `D_PROVINCE` | 省份 | enum | 浙江、广东 | sales |
| `D_SALES_CHANNEL` | 销售渠道 | enum | app、web、offline | sales |
| `D_PRODUCT` | 商品 | entity | SKU 名称 | sales |
| `D_CATEGORY` | 商品品类 | enum | 食品、数码 | sales |
| `D_USER_TYPE` | 用户类型 | enum | new、existing | sales |
| `D_AD_PLATFORM` | 广告平台 | enum | ocean、wechat、search | advertising |
| `D_AD_ACCOUNT` | 广告账户 | entity | account_001 | advertising |
| `D_CAMPAIGN` | 广告计划 | entity | 新客拉新计划 | advertising |
| `D_CREATIVE` | 广告素材 | entity | creative_001 | advertising |
| `D_DEVICE_TYPE` | 设备类型 | enum | ios、android、web | advertising |
| `D_ATTRIBUTION_WINDOW` | 归因窗口 | enum | 1d、7d | advertising |

## 4. 电商经营域指标

### 4.1 指标总表

| 指标 ID | 名称 | 类型 | 单位 | 默认聚合 | 模型 |
| --- | --- | --- | --- | --- | --- |
| `M_SALES_GMV` | GMV | amount | CNY | sum | `SM_SALES_ORDER_ITEM` |
| `M_SALES_PAID_REVENUE` | 已支付销售额 | amount | CNY | sum | `SM_SALES_ORDER_ITEM` |
| `M_SALES_ORDER_COUNT` | 支付订单量 | count | order | count_distinct | `SM_SALES_ORDER` |
| `M_SALES_BUYER_COUNT` | 支付买家数 | count | user | count_distinct | `SM_SALES_ORDER` |
| `M_SALES_ITEM_QUANTITY` | 销售件数 | count | item | sum | `SM_SALES_ORDER_ITEM` |
| `M_SALES_AVG_ORDER_VALUE` | 客单价 | average | CNY/order | ratio | 派生 |
| `M_SALES_REFUND_AMOUNT` | 退款金额 | amount | CNY | sum | `SM_SALES_ORDER` |
| `M_SALES_REFUND_RATE` | 金额退款率 | ratio | % | ratio | 派生 |
| `M_SALES_GROSS_PROFIT` | 毛利额 | amount | CNY | sum | `SM_SALES_ORDER_ITEM` |
| `M_SALES_GROSS_MARGIN_RATE` | 毛利率 | ratio | % | ratio | 派生 |
| `M_SALES_NEW_BUYER_COUNT` | 新客数 | count | user | count_distinct | `SM_SALES_BUYER_DAY` |
| `M_SALES_REPEAT_PURCHASE_RATE` | 复购率 | ratio | % | ratio | `SM_SALES_BUYER_DAY` |

### 4.2 详细定义

#### `M_SALES_GMV` — GMV

- 业务定义：用户提交订单对应的商品成交总额，不因后续退款减少。
- 公式：`SUM(order_item_gross_amount)`。
- 过滤：排除测试订单、已取消且未支付订单。
- 别名：成交总额、商品交易总额、交易额。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道、商品、品类。
- 注意：GMV 不等于企业确认收入；在指标详情中必须展示差异说明。

#### `M_SALES_PAID_REVENUE` — 已支付销售额

- 业务定义：统计期内成功支付的商品金额，退款单独通过退款指标体现。
- 公式：`SUM(paid_item_amount)`。
- 过滤：支付状态为成功，排除测试订单。
- 别名：支付金额、支付销售额、实付销售额。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道、商品、品类。

#### `M_SALES_ORDER_COUNT` — 支付订单量

- 业务定义：统计期内至少成功支付一次的去重订单数。
- 公式：`COUNT_DISTINCT(order_id)`。
- 别名：支付订单数、成交订单量、订单量。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道。
- 歧义：用户只说“订单量”时，如果语境可能指提交订单量，应进入澄清。

#### `M_SALES_BUYER_COUNT` — 支付买家数

- 业务定义：统计期内至少完成一笔成功支付订单的去重用户数。
- 公式：`COUNT_DISTINCT(user_id)`。
- 别名：购买用户数、支付用户数、买家数。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道、用户类型。

#### `M_SALES_ITEM_QUANTITY` — 销售件数

- 业务定义：成功支付订单中的商品数量总和。
- 公式：`SUM(paid_quantity)`。
- 别名：销量、销售数量、售出件数。
- 支持维度：日期、周、月、季度、地区、渠道、商品、品类。

#### `M_SALES_AVG_ORDER_VALUE` — 客单价

- 业务定义：每个支付订单的平均已支付销售额。
- 公式：`M_SALES_PAID_REVENUE / M_SALES_ORDER_COUNT`。
- 分母为 0：返回 `null`。
- 别名：平均订单金额、平均客单价、AOV。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道。

#### `M_SALES_REFUND_AMOUNT` — 退款金额

- 业务定义：统计期内退款成功的金额，时间口径按退款成功时间。
- 公式：`SUM(refund_success_amount)`。
- 别名：成功退款金额、退款额。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道、商品、品类。
- 注意：与按原订单日期回溯的退款口径不同，首版采用退款发生时间口径。

#### `M_SALES_REFUND_RATE` — 金额退款率

- 业务定义：统计期退款成功金额占同期已支付销售额的比例。
- 公式：`M_SALES_REFUND_AMOUNT / M_SALES_PAID_REVENUE`。
- 分母为 0：返回 `null`。
- 别名：退款率、金额退款比例。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道、商品、品类。
- 歧义：与订单退款率不同；用户只说“退款率”时应展示口径说明或澄清。

#### `M_SALES_GROSS_PROFIT` — 毛利额

- 业务定义：已支付销售额扣除成功退款和对应销售商品成本后的金额。
- 公式：`SUM(paid_item_amount - allocated_refund_amount - recognized_item_cost)`。
- 别名：毛利、销售毛利、主营毛利额。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道、商品、品类。
- 歧义：用户只说“毛利”时，与毛利率组成候选并进入澄清。

#### `M_SALES_GROSS_MARGIN_RATE` — 毛利率

- 业务定义：毛利额占扣除退款后销售收入的比例。
- 公式：`M_SALES_GROSS_PROFIT / (M_SALES_PAID_REVENUE - M_SALES_REFUND_AMOUNT)`。
- 分母小于等于 0：返回 `null`。
- 别名：销售毛利率、主营业务毛利率、毛利比例。
- 支持维度：日期、周、月、季度、地区、省份、销售渠道、商品、品类。

#### `M_SALES_NEW_BUYER_COUNT` — 新客数

- 业务定义：用户历史首次支付日期落在统计期内的去重用户数。
- 公式：`COUNT_DISTINCT(user_id WHERE first_paid_date in time_range)`。
- 别名：新增购买用户、首购用户数、新买家数。
- 支持维度：日期、周、月、季度、地区、销售渠道。
- 注意：首版按平台历史首购定义，不按渠道首购定义。

#### `M_SALES_REPEAT_PURCHASE_RATE` — 复购率

- 业务定义：观察期内完成至少两笔支付订单的用户数，占完成至少一笔支付订单用户数的比例。
- 公式：`repeat_buyer_count / M_SALES_BUYER_COUNT`。
- 分母为 0：返回 `null`。
- 别名：重复购买率、复购用户比例。
- 支持维度：月、季度、地区、销售渠道。
- 限制：不支持按日计算；首版最小统计粒度为月。

## 5. 广告投放域指标

### 5.1 指标总表

| 指标 ID | 名称 | 类型 | 单位 | 默认聚合 | 模型 |
| --- | --- | --- | --- | --- | --- |
| `M_AD_IMPRESSIONS` | 曝光量 | count | impression | sum | `SM_AD_DELIVERY_DAY` |
| `M_AD_CLICKS` | 点击量 | count | click | sum | `SM_AD_DELIVERY_DAY` |
| `M_AD_SPEND` | 广告消耗 | amount | CNY | sum | `SM_AD_DELIVERY_DAY` |
| `M_AD_CONVERSIONS` | 归因转化量 | count | conversion | sum | `SM_AD_ATTRIBUTION` |
| `M_AD_ATTRIBUTED_REVENUE` | 归因收入 | amount | CNY | sum | `SM_AD_ATTRIBUTION` |
| `M_AD_CTR` | 点击率 | ratio | % | ratio | 派生 |
| `M_AD_CPC` | 单次点击成本 | average | CNY/click | ratio | 派生 |
| `M_AD_CPM` | 千次曝光成本 | average | CNY/1000 impressions | ratio | 派生 |
| `M_AD_CVR` | 点击转化率 | ratio | % | ratio | 派生 |
| `M_AD_CPA` | 单次转化成本 | average | CNY/conversion | ratio | 派生 |
| `M_AD_ROAS` | 广告支出回报 | ratio | multiple | ratio | 派生 |
| `M_AD_ROI` | 广告投资回报率 | ratio | % | ratio | 派生 |

### 5.2 详细定义

#### `M_AD_IMPRESSIONS` — 曝光量

- 业务定义：广告被有效展示的次数。
- 公式：`SUM(valid_impressions)`。
- 别名：展示量、曝光次数、impressions。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备。

#### `M_AD_CLICKS` — 点击量

- 业务定义：广告产生的有效点击次数。
- 公式：`SUM(valid_clicks)`。
- 别名：点击次数、clicks。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备。

#### `M_AD_SPEND` — 广告消耗

- 业务定义：平台确认的广告投放消耗金额。
- 公式：`SUM(ad_spend_amount)`。
- 别名：投放消耗、广告花费、投放成本、spend。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备。

#### `M_AD_CONVERSIONS` — 归因转化量

- 业务定义：在选定归因窗口内归因到广告点击的有效转化次数。
- 公式：`SUM(attributed_conversions)`。
- 别名：转化数、归因订单量、conversion。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备、归因窗口。
- 注意：结果必须展示归因窗口。

#### `M_AD_ATTRIBUTED_REVENUE` — 归因收入

- 业务定义：在选定归因窗口内归因到广告投放的订单已支付销售额。
- 公式：`SUM(attributed_paid_revenue)`。
- 别名：广告归因收入、投放收入、归因销售额。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备、归因窗口。

#### `M_AD_CTR` — 点击率

- 业务定义：有效点击量占有效曝光量的比例。
- 公式：`M_AD_CLICKS / M_AD_IMPRESSIONS`。
- 分母为 0：返回 `null`。
- 别名：CTR、点击转化率（不推荐，可能与 CVR 混淆）。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备。

#### `M_AD_CPC` — 单次点击成本

- 业务定义：每次有效点击对应的平均广告消耗。
- 公式：`M_AD_SPEND / M_AD_CLICKS`。
- 分母为 0：返回 `null`。
- 别名：CPC、平均点击成本、点击单价。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备。

#### `M_AD_CPM` — 千次曝光成本

- 业务定义：每一千次有效曝光对应的平均广告消耗。
- 公式：`M_AD_SPEND * 1000 / M_AD_IMPRESSIONS`。
- 分母为 0：返回 `null`。
- 别名：CPM、千次展示成本。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备。

#### `M_AD_CVR` — 点击转化率

- 业务定义：归因转化量占有效点击量的比例。
- 公式：`M_AD_CONVERSIONS / M_AD_CLICKS`。
- 分母为 0：返回 `null`。
- 别名：CVR、转化率、点击转化率。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备、归因窗口。
- 歧义：用户只说“转化率”时应根据广告语境选 CVR，否则澄清。

#### `M_AD_CPA` — 单次转化成本

- 业务定义：每次归因转化对应的平均广告消耗。
- 公式：`M_AD_SPEND / M_AD_CONVERSIONS`。
- 分母为 0：返回 `null`。
- 别名：CPA、转化成本、获客成本（不推荐，获客口径可能不同）。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备、归因窗口。

#### `M_AD_ROAS` — 广告支出回报

- 业务定义：广告归因收入与广告消耗的倍数。
- 公式：`M_AD_ATTRIBUTED_REVENUE / M_AD_SPEND`。
- 分母为 0：返回 `null`。
- 别名：ROAS、广告回报倍数、投产比。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备、归因窗口。
- 歧义：中文“ROI”有时实际指 ROAS，必须展示候选定义。

#### `M_AD_ROI` — 广告投资回报率

- 业务定义：广告归因收入扣除广告消耗后的净回报，占广告消耗的比例；未计商品成本和其他经营成本。
- 公式：`(M_AD_ATTRIBUTED_REVENUE - M_AD_SPEND) / M_AD_SPEND`。
- 分母为 0：返回 `null`。
- 别名：ROI、投放投资回报率、广告净回报率。
- 支持维度：日期、周、月、广告平台、账户、计划、素材、设备、归因窗口。
- 注意：这不是完整经营利润 ROI，详情页必须显示范围限制。

## 6. 指标歧义规则

| 用户表达 | 候选 | 推荐行为 |
| --- | --- | --- |
| 毛利 | 毛利额、毛利率 | `CLARIFY` |
| 退款率 | 金额退款率、未来订单退款率 | MVP 只有金额退款率，展示口径并确认 |
| 订单量 | 支付订单量、提交订单量 | 若无支付语境则 `CLARIFY` |
| 销售额 | GMV、已支付销售额、归因收入 | 根据业务域和上下文门控，证据不足则澄清 |
| 转化率 | 支付转化率、广告 CVR | 根据业务域过滤，跨域问题需澄清 |
| ROI / 投产 | ROAS、广告 ROI | `CLARIFY` 或展示两者定义 |
| 获客成本 | CPA、CAC | MVP 只有 CPA，不允许直接把 CPA 当 CAC |

## 7. 首发指标验收

每个指标发布前必须满足：

- [ ] 指标 ID、名称、别名和业务说明完整。
- [ ] 公式能够表达为受限 AST。
- [ ] 分子、分母、空值和除零规则明确。
- [ ] 默认时间字段和支持维度明确。
- [ ] 语义模型、来源字段和 Join 路径可解析。
- [ ] 至少 3 条正常问题和 1 条歧义/边界问题进入黄金集。
- [ ] 与手工基准 SQL 的结果一致。
- [ ] 指标详情页能够说明与相似指标的区别。

## 8. 后续指标候选

MVP 完成后再考虑：提交订单量、支付转化率、订单退款率、净收入、库存周转、用户留存、CAC、LTV、自然流量转化、渠道增量和利润口径 ROI。

这些指标依赖新增事实、漏斗、用户生命周期或成本模型，不应为了增加指标数量在 MVP 中给出不完整口径。
