# Olist Brazilian E-Commerce

Source: [Kaggle - Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

DataPath 使用该公开匿名数据集验证电商多表 ChatBI。数据覆盖约 10 万笔 2016-2018 年巴西市场订单。

## 本地准备

```bash
uv run python -m scripts.download_olist
uv run python -m scripts.load_olist
uv run python -m scripts.validate_olist
```

九个 CSV 默认不纳入 Git；`relationships.json` 保存表粒度、基数和推荐 Join 契约。公开分发原始数据前需再次核对数据集许可和 Kaggle 条款。

## 当前产品状态

- 九张 ClickHouse 表：已加载并校验。
- Semantic Model / Entity：已建立；支付、评价和地理模型部分暂存。
- 已发布指标：12 个。
- 已发布安全 Join：5 条。
- 多表自然语言问数：已实现。
- 支付/评价多事实查询：未实现，等待 Aggregate-Before-Join。
- 地理 Zip Prefix 关系：未发布，避免多行映射导致 Fanout。

数据快照与行数见 `data/evaluation/golden/olist_golden_manifest.json`，指标口径见 `document/initial-metric-catalog.md`。
