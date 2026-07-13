# Olist 黄金测试集

这套冻结测试集用于衡量 DataPath 的检索、状态门禁、SQL 编译、查询执行和多轮上下文能力。测试问题基于冻结的 Olist 数据快照生成，当前覆盖 12 个已发布指标和已发布的安全 Join 路径。

## 数据划分

| 文件 | 用途 | 数量 |
|---|---|---:|
| `olist_golden_development.json` | 日常开发与 Bad Case 定位 | 220 |
| `olist_golden_regression.json` | 发布前固定回归 | 80 |
| `olist_golden_blind.json` | 最终留出评估 | 60 |
| `olist_golden_manifest.json` | 快照行数、指标版本与分布清单 | - |

共 360 条用例。正式回归结果写入 `reports/olist-expanded-metrics-regression.json` 和同名 Markdown 报告。

## 覆盖分布

| 类型 | 数量 |
|---|---:|
| 核心指标查询 | 100 |
| 已治理多实体查询 | 100 |
| 语义鲁棒性 | 30 |
| 歧义澄清 | 20 |
| 多轮上下文 | 40 |
| 能力边界与安全拒绝 | 35 |
| 权限阻断 | 15 |
| 数据边界场景 | 20 |

成功类单轮用例包含独立计算的 ClickHouse Oracle，包括结果行数、结果校验和、总计、Top 值、误差范围和规范 SQL 校验和。测试用例不保存规范 SQL 正文，避免产品编译器复用答案。

## 防泄漏规则

- 开发集可以用于定位问题，但不得把完整问题批量复制进语义画像。
- 回归集不得成为 Prompt 的 Few-shot 示例。
- 盲测问题不得写入别名、BM25 文档、向量索引样例或手写匹配规则。
- 公共仓库只能实现逻辑隔离；用于招聘或生产验收的真正盲测集及 Oracle 应保存在私有位置。

## 重建与执行

基于冻结快照重建：

```bash
python -m scripts.build_olist_golden_dataset
```

执行 80 条固定回归：

```bash
python -m scripts.evaluate_olist_golden_dataset --split regression
```

任何数据表行数或校验和变化都必须经过快照版本评审，不得为了让失败用例通过而静默改写预期答案。
