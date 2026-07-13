# DataPath 产品文档中心

> 文档基线：V2.0
> 更新日期：2026-07-13
> 产品阶段：作品集 MVP，进入质量与治理增强阶段

## 统一定义

DataPath 是面向具备 SQL 基础的数据运营和数据分析师的可信 ChatBI Copilot。它通过受治理的指标与 Join 语义层，把自然语言问题转为可校验的 Query DSL，再由服务端确定性编译和执行 SQL，返回交互式数据结果与可追溯 Evidence。

当前产品只承诺 Olist 演示数据上的能力，不将离线测评包装为真实客户收益。

## 正式文档

| 文档 | 用途 | 当前状态 |
| --- | --- | --- |
| [00 项目理解报告](00-project-understanding.md) | 产品事实、用户、流程、模块和边界 | 当前基线 |
| [01 产品需求文档](01-product-requirements.md) | 产品范围、用户故事、规则和验收 | 当前基线 |
| [02 产品路线图](02-roadmap.md) | 已完成能力和后续版本目标 | 持续维护 |
| [03 AI 与可信架构](03-ai-capability.md) | LLM、检索、Agent、Memory、Tool 与确定性边界 | 当前基线 |
| [04 用户体验](04-user-experience.md) | 六个页面、状态和交互规则 | 当前基线 |
| [05 产品指标与评测](05-metrics-evaluation.md) | 360 条黄金集、发布回归和质量门禁 | 当前基线 |
| [06 数据权限与安全](06-data-permission-security.md) | 当前安全控制和生产差距 | 当前基线 |
| [07 商业化与作品集](07-commercial-portfolio.md) | 对外表达、商业假设和证据边界 | 当前基线 |
| [08 需求池](08-backlog.md) | 下一迭代优先级与完成标准 | 持续维护 |
| [09 Olist 数据与多表能力](09-olist-multitable-evaluation.md) | 九表、12 指标、Join 边界和测评 | 当前基线 |
| [12 指标语义检索架构](12-semantic-retrieval-architecture.md) | BM25、Embedding、Reranker 与置信门禁 | 当前基线 |
| [15 Semantic Join Graph 治理](15-semantic-join-graph-governance.md) | 关系发现、验证、版本和发布 | 当前基线 |

## 配套交付物

| 文档或契约 | 用途 |
| --- | --- |
| [当前指标目录](../initial-metric-catalog.md) | 12 个已发布指标及口径 |
| [作品集一页总览](../portfolio-one-page-overview.md) | 面试和项目展示摘要 |
| [产品决策说明](../product-decision-rationale.md) | 关键取舍与答辩材料 |
| [Dify Workflow 导入手册](../dify-chatbi-workflow-import.md) | 可选内部工作流导入与联调 |
| [OpenAPI](../chatbi-openapi.yaml) | 八个受保护内部 ChatBI 接口 |
| [Query DSL Schema](../query-dsl-v1.schema.json) | DSL 1.0 契约；Olist 在线入口使用兼容的 DSL 2.0 扩展 |
| [Olist 黄金集](../../data/evaluation/golden/README.md) | 360 条开发、回归和盲测数据 |
| [最新回归报告](../../reports/olist-expanded-metrics-regression.md) | 80 条发布回归的当前结果 |

## 事实优先级

文档发生冲突时按以下顺序判断：

1. 当前代码、数据库 Schema、自动测试和可复现运行结果。
2. 本目录当前基线文档。
3. OpenAPI、Query DSL、Dify DSL 等机器契约。
4. 生成型测评报告。
5. 路线图和商业假设。

## 维护规则

- 产品名称统一为 `DataPath`。
- 当前数据域统一为 Olist，禁止继续引用旧 UCI、模拟销售或广告数据作为现状。
- 指标数量、Join 状态和测评结果必须附日期与样本量。
- 规划能力必须明确标记为“未实现”或“下一版本”。
- 每次修改指标、检索、Join、权限或上下文行为时，至少同步 PRD、架构、评测和需求池。
- 阶段验收快照和中间测评报告不进入正式文档中心；有长期价值的结论应合并到当前基线。
