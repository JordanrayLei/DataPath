# DataPath Olist 数据与多表能力

> 版本：V2.0
> 更新日期：2026-07-13

## 1. 数据集

DataPath 当前只使用 Olist Brazilian E-Commerce 作为产品主数据。该公开匿名数据集包含 2016-2018 年巴西电商订单、商品、客户、卖家、支付、评价和地理信息。

| 表 | 快照行数 | 当前状态 |
| --- | ---: | --- |
| `olist_orders` | 99,441 | ACTIVE |
| `olist_order_items` | 112,650 | ACTIVE，当前指标基准事实表 |
| `olist_order_payments` | 103,886 | STAGED，多事实 |
| `olist_order_reviews` | 99,224 | STAGED，多事实 |
| `olist_customers` | 99,441 | ACTIVE |
| `olist_products` | 32,951 | ACTIVE |
| `olist_sellers` | 3,095 | ACTIVE |
| `olist_geolocation` | 1,000,163 | STAGED，存在 Zip Prefix 多行 |
| `olist_product_category_translation` | 71 | ACTIVE |

完整快照见 `data/evaluation/golden/olist_golden_manifest.json`。

## 2. 当前指标

已发布 12 个指标：商品销售额、运费、订单量、成交总额、客单价、平均每单运费、运费率、商品件数、每单商品件数、成交商品数、活跃卖家数和购买客户数。

所有指标版本当前为 v1，详细公式和边界见 [指标目录](../initial-metric-catalog.md)。

## 3. Semantic Join Graph

已发布安全关系：

1. 订单商品 -> 订单。
2. 订单商品 -> 商品。
3. 订单商品 -> 卖家。
4. 订单 -> 客户。
5. 商品 -> 品类翻译。

这些关系均为 `many_to_one + safe`，Planner 可以从订单商品事实表确定性找到所需维度路径。

暂存关系：

- 支付 -> 订单：`aggregate_before_join`。
- 评价 -> 订单：`aggregate_before_join`。

当前禁止同时连接订单商品与支付/评价后直接聚合，因为一对多事实组合会放大金额和计数。

## 4. 查询能力

已支持：

- 整体聚合与按月趋势。
- 按商品品类、客户州、卖家州和订单状态拆分或排名。
- 指标在单实体或安全多实体路径上执行。
- 多轮继承指标、维度和时间。
- SQL 编译时输出模型与字段血缘。

未支持：

- 支付金额按商品品类等多事实分析。
- 评价分数按商品、卖家或客户维度分析。
- 自由 Join、地理经纬度空间分析、退款和成本指标。

## 5. 测评

Olist 黄金集共 360 条，包含核心指标、多实体、语义鲁棒性、歧义、多轮、安全、权限和数据边界。

当前发布回归运行 80 条：

- 严格通过 73 条，91.25%。
- 核心指标 24/24。
- 多实体 24/24。
- 多轮 8/8。
- 语义鲁棒性 7/7。
- 数据边界 3/3。
- 剩余 7 条为状态门禁分类差异。

报告见 [olist-expanded-metrics-regression.md](../../reports/olist-expanded-metrics-regression.md)。

## 6. 数据质量边界

- Olist 数据尾部月份并不都完整，时间示例和 Oracle 必须使用冻结快照。
- 订单商品每行代表一个订单商品项；“商品件数”以明细行数计。
- 客单价定义为商品销售额 / 去重订单量，不含运费。
- 成交总额定义为商品价格 + 运费，不等同支付表实际支付金额。
- 购买客户数使用 `customer_unique_id` 去重，不使用订单级 `customer_id`。

## 7. 后续演进

下一阶段先实现按目标粒度聚合各事实表，再发布支付与评价 Join；新增指标必须同时提供公式、粒度、Join 策略、维度范围和独立 SQL Oracle。
