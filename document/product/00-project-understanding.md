# DataPath 项目理解报告

> 版本：V2.0
> 更新日期：2026-07-13
> 依据：当前代码、Olist 数据快照、43 项自动测试和最新发布回归

## 产品简介

DataPath 是面向具备 SQL 基础的数据运营和数据分析师的可信 ChatBI Copilot。它解决高频、重复、必要但低价值的 SQL 查数工作，让用户把更多时间投入分析、归因和决策支持。

产品不是自由 NL2SQL：用户问题必须先映射到已发布指标和可用维度，再生成 Query DSL，由服务端根据白名单字段和已发布 Join Graph 编译 SQL。结果经过 Profiler、Evidence 和 Reflection 后才展示。

## 产品目标

- 提升标准聚合、趋势和排名查询的完成效率。
- 统一指标名称、定义、公式、单位、维度、版本和血缘。
- 降低指标误选、错误 Join、SQL 越权和无证据解读风险。
- 支持连续追问，减少重复描述指标、维度和时间范围。
- 将失败问题沉淀为 Bad Case 和黄金问题，形成可测量的质量闭环。
- 辅助定位异常和缩小归因范围，不自动声称完成因果归因。

## 用户画像

首期用户是需要频繁查数、了解基本 SQL 和业务指标的数据运营及数据分析师。他们希望快速得到答案，同时仍能检查指标口径、SQL、数据血缘和查询限制。

不懂 SQL 的普通业务人员是未来扩展用户，不是当前产品验证的首要对象。

## 核心流程

```text
自然语言问题
-> 加载会话上下文
-> Query Understanding
-> Hybrid Metric Retrieval
-> PASS / CLARIFY / REJECT / BLOCKED
-> Query DSL 2.0
-> DSL Validator
-> Semantic Join Graph + Deterministic Planner
-> SQL Compiler
-> ClickHouse 只读执行
-> Result Profiler + Evidence
-> Interpretation + Reflection
-> 交互式结果 / Data-only 降级
```

成功查询会保存本轮指标、维度、筛选和时间范围，供同一会话后续问题继承。新会话不会继承旧会话上下文。

## 功能模块

| 模块 | 已实现能力 |
| --- | --- |
| 问数工作台 | 自然语言提问、多轮上下文、表格、图表、解读、SQL 查看与复制、执行链路 |
| 指标口径中心 | 12 个已发布指标的定义、别名、公式、维度、版本、模型和血缘 |
| 指标管理 | 草稿创建、公式校验、维度校验、不可变递增版本发布 |
| Join 治理 | 语义模型、关系草稿、候选扫描、基数/覆盖率/Fanout 检测、发布 |
| 质量运营 | Bad Case 提交、状态推进、黄金问题和回归候选 |
| 测评监控 | 最新入口测评、历史趋势、通过率、失败门禁和延迟 |

## AI 与 Agent 能力

DataPath 属于 Agentic Workflow，不是多 Agent 自治系统。

- 在线入口默认使用确定性的 Query Understanding Provider。
- 指标检索使用名称/别名规则、BM25、百炼 `text-embedding-v3` 和 `qwen3-rerank`。
- Dify DSL 提供可选的 LLM 预处理、消歧、DSL 草稿与修订工作流，但不参与数据权限和 SQL 安全决策。
- Memory 是 PostgreSQL 中的会话级结构化上下文，不是长期用户画像或向量记忆。
- 当前没有 MCP；后端服务调用属于受控 Tool/API 调用。

## 数据与技术架构

| 层级 | 当前实现 |
| --- | --- |
| 前端 | 原生 HTML、CSS、JavaScript，由 FastAPI 托管 |
| 应用 | FastAPI、Pydantic、SQLAlchemy |
| 元数据与审计 | PostgreSQL 16 + pgvector |
| 数仓 | ClickHouse 25.8，Olist 九表 |
| 检索 | 规则 + BM25 + Embedding + Reranker |
| 编排 | FastAPI BFF 为当前在线主链；Dify 为可选内部资产 |
| 基础设施 | Docker Compose；Redis 已部署但非主链状态依赖 |
| 契约 | Query DSL、OpenAPI、签名执行 Token |

## 当前验证结果

- Olist 九表：订单 99,441 行，订单商品 112,650 行，其他表行数见黄金集 Manifest。
- 12 个已发布指标、5 条已发布安全 Join、2 条多事实 Join 暂存。
- 121 条指标语义向量文档和 9 条能力边界样本。
- 自动测试 43/43 通过。
- 最新 80 条发布回归：73/80，91.25%。核心指标、多实体、多轮、语义鲁棒性和数据边界均为 100%。

这些结果来自本地离线环境，不代表真实客户准确率或生产 SLA。

## 当前边界

- 没有真实用户访谈、试点客户、生产数据或量化效率收益。
- 当前只有 Olist 演示数据与 `demo` 工作空间。
- 支付、评价等多事实查询尚未启用 Aggregate-Before-Join。
- 不支持用户自助接入真实数据源、自由 Join、任意 SQL、数据写回或明细批量导出。
- 企业 SSO、RBAC、行列权限、敏感字段脱敏和多租户隔离未实现。
- 指标有草稿和发布，但没有多人提交、审核、驳回、废弃和影响分析闭环。
- 安全动作分类仍有 7 条已知回归 Bad Case。

## 下一阶段

1. 统一 `CLARIFY`、`REJECT`、`BLOCKED` 状态语义并关闭 7 条回归 Bad Case。
2. 完成指标审批、废弃与变更影响分析。
3. 增加数据源连接、Schema 扫描和语义模型映射。
4. 实现元数据同步任务和 Join Relation 变更候选。
5. 在验证 Fanout 安全后实现支付与评价的 Aggregate-Before-Join。
6. 引入真实目标用户任务和外部盲测，验证实际效率与准确率。
