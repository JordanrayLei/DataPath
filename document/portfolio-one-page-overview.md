# DataPath｜一页作品集总览

> 更新日期：2026-07-13
> 项目性质：可运行作品集 MVP，不宣称企业生产上线

## 项目一句话

DataPath 是面向具备 SQL 基础的数据运营和数据分析师的可信 ChatBI Copilot，通过指标语义层、Query DSL、Semantic Join Graph 和确定性 SQL Compiler，把自然语言问题转为可追溯的数据答案。

## 我的角色

独立 AI 产品负责人 / 独立开发者，负责产品定位、需求、体验、AI 架构、指标与 Join 治理、可信机制、数据准备、评测体系和代码落地。

## 用户问题

数据运营和分析师需要反复完成标准聚合、趋势和排名查询。手写 SQL 占用分析时间；直接 NL2SQL 又容易产生口径错误、错误 Join、越权 SQL 和无证据结论。

## 产品方案

```text
自然语言
-> Hybrid Metric Retrieval
-> Query DSL
-> Semantic Join Graph + Planner
-> SQL Compiler
-> ClickHouse
-> Evidence + Reflection
-> 交互式结果
```

系统把 AI 用于理解、检索和编排，把指标发布、Join 选择、SQL 生成、执行和可信校验保留在确定性服务端。

## 已实现能力

| 模块 | 当前能力 |
| --- | --- |
| 问数 | 聚合、趋势、排名、多轮上下文、SQL 查看与复制 |
| 指标 | 12 个发布指标、草稿校验、不可变版本发布 |
| 多表 | Olist 九表、5 条发布 Join、Deterministic Planner |
| 检索 | BM25 + `text-embedding-v3` + `qwen3-rerank` |
| 可信 | Evidence、Reflection、Fail-closed、数据降级 |
| 治理 | Join Relation 草稿/检测/发布、Bad Case、黄金问题 |
| 测评 | 360 条黄金集、80 条发布回归、入口 Smoke 与趋势 |

## 验证结果

- 自动测试：43/43。
- 产品入口 Smoke：36/36。
- Olist 发布回归：73/80，91.25%。
- 核心指标、多实体、多轮、语义鲁棒性和数据边界：当前回归切片均 100%。
- 开放问题：7 条状态门禁标签不一致。

所有结果来自本地 Olist 快照，不等同真实用户准确率或生产 SLA。

## 产品亮点

1. 不让 LLM 直接生成并执行 SQL。
2. 指标和 Join 都有发布状态、版本和验证门禁。
3. 完整指标名优先，Embedding 与 Reranker 只负责受控召回排序。
4. 数字结论由 Evidence 绑定，Reflection 在展示前复核。
5. 失败问题可以进入 Bad Case 和黄金回归，而不是只修 Prompt。

## 当前边界

- 只有 Olist 演示数据和 demo 工作空间。
- 没有真实用户、生产数据或商业收益验证。
- 支付与评价多事实查询尚未实现 Aggregate-Before-Join。
- 没有企业 SSO、RBAC、行列权限和多租户隔离。
- 没有数据源自助接入、Schema 定时同步和指标多人审批。

## 下一步

P0 关闭 7 条状态门禁 Bad Case；随后完成指标审批/废弃/影响分析、元数据同步、数据源接入和 Aggregate-Before-Join。

## 面试开场

> DataPath 不是一个让模型自由写 SQL 的聊天机器人。我把语言理解与检索交给 AI，把指标、Join、SQL、执行和证据校验放在确定性服务端，并用 360 条黄金集持续验证。当前在 Olist 九表上发布 12 个指标和 5 条安全 Join，80 条发布回归严格通过率为 91.25%，剩余问题也以 Bad Case 形式透明管理。
