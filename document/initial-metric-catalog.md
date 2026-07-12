# DataPath Olist V1 指标目录

> 版本：V1.0  
> 数据域：Olist 巴西电商经营  
> 发布状态：PUBLISHED

## 语义模型

V1 以 `SM_OLIST_ORDER_ITEMS` 为基础事实模型，通过受治理的 Semantic Join Graph 连接订单、商品、客户、卖家和品类翻译维度。支付和评价为事实表，在 Aggregate-Before-Join 编译器完成前保持 `STAGED`，禁止跨事实表查询。

## 已发布指标

#### `M_OLIST_ITEM_REVENUE` - Olist商品销售额

- 定义：Olist 订单商品价格之和，不包含运费。
- 公式：`SUM(price)`。
- 单位：BRL。
- 时间口径：订单购买时间 `order_purchase_timestamp`。
- 支持维度：日期、月份、商品品类、客户州、卖家州、订单状态。

#### `M_OLIST_FREIGHT_VALUE` - Olist运费

- 定义：Olist 订单商品行运费之和。
- 公式：`SUM(freight_value)`。
- 单位：BRL。
- 时间口径：订单购买时间。
- 支持维度：日期、月份、商品品类、客户州、卖家州、订单状态。

#### `M_OLIST_ORDER_COUNT` - Olist订单量

- 定义：订单商品事实中的去重订单数。
- 公式：`COUNT_DISTINCT(order_id)`。
- 单位：order。
- 时间口径：订单购买时间。
- 支持维度：日期、月份、商品品类、客户州、卖家州、订单状态。

## 能力边界

- 不支持成本、毛利、广告、库存、优惠券、客户人口属性和预测。
- 不支持支付、评价与订单商品的跨事实联查，防止 Fanout 造成重复聚合。
- 无法唯一确定指标时返回澄清，不生成 SQL。
