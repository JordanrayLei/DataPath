# DataPath 产品文档中心

> 文档集版本：V1.0  
> 基线日期：2026-07-11  
> 产品阶段：作品集 MVP  
> 维护角色：产品负责人

## 1. 文档目的

本目录是 DataPath 的正式产品文档入口，服务于内部沉淀、项目交付、作品集展示、面试说明和版本迭代。历史设计、技术验收与联调记录继续保留在 `document/`，但产品范围、用户定位和版本状态以本目录为准。

## 2. 统一产品定义

DataPath 是面向具备 SQL 基础的数据运营和数据分析师的可信 ChatBI Copilot。用户通过自然语言提出查数问题，系统在统一指标口径下生成 Query DSL，由确定性服务编译并安全执行 SQL，返回表格、图表、业务解读和可追溯 Evidence。

## 3. 文档清单

| 编号 | 文档 | 主要用途 | 状态 |
| --- | --- | --- | --- |
| 00 | [项目理解报告](00-project-understanding.md) | 统一项目事实与产品边界 | V1.0 |
| 01 | [产品需求文档 PRD](01-product-requirements.md) | 产品范围、流程、规则与验收 | V1.0 |
| 02 | [版本路线图](02-roadmap.md) | 版本目标、优先级与依赖 | V1.0 |
| 03 | [AI 能力与可信架构](03-ai-capability.md) | LLM、Workflow、Prompt、RAG、Memory、Tool | V1.0 |
| 04 | [用户体验与页面说明](04-user-experience.md) | 页面、状态和交互规则 | V1.0 |
| 05 | [产品指标与评测方案](05-metrics-evaluation.md) | 成功指标、黄金集和发布门禁 | V1.0 |
| 06 | [数据、权限与安全](06-data-permission-security.md) | 数据边界、权限现状和企业化目标 | V1.0 |
| 07 | [商业化与作品集说明](07-commercial-portfolio.md) | 商业假设、项目价值和对外表达 | V1.0 |
| 08 | [需求池与迭代管理](08-backlog.md) | Epic、优先级和验收出口 | V1.0 |
| 09 | [Olist多表业务测评报告](09-olist-multitable-evaluation.md) | 30条业务用例、6个可信门禁与能力边界 | V1.0 |
| 12 | [指标语义检索长期架构](12-semantic-retrieval-architecture.md) | 动态语义资产、混合召回与安全门禁 | V1.0 |
| 13 | [Embedding向量索引实施报告](13-embedding-vector-index-report.md) | 百炼Embedding、pgvector与能力边界门控 | V1.0 |
| 14 | [Olist多表数据准备说明](14-olist-multitable-data-preparation.md) | 九张关系表、Join契约和后续实施边界 | V1.0 |
| 15 | [Semantic Join Graph治理工作台](15-semantic-join-graph-governance.md) | 自动发现、Fanout检测、草稿审核与版本发布 | V1.0 |

## 4. 状态口径

| 标记 | 定义 |
| --- | --- |
| 已实现 | 代码、接口和测试能够证明的当前能力 |
| 部分实现 | 已有底层模型或局部链路，但用户闭环尚未完成 |
| 下一版本 | 已确定优先级，尚未完成开发 |
| 远期规划 | 产品方向成立，但尚未进入承诺版本 |
| 待验证 | 缺少真实用户、客户或实验数据支撑的假设 |

## 5. 事实优先级

发生冲突时采用以下顺序：

1. 当前代码、接口、自动测试和可复现测评。
2. 本目录中的产品基线文档。
3. Dify Workflow DSL 和技术契约。
4. 历史 PRD、验收记录和作品集材料。
5. 尚未验证的产品设想。

## 6. 版本维护规则

- 产品名称统一使用 `DataPath`。
- 当前首要用户统一为具备 SQL 基础的数据运营和数据分析师。
- 不将模拟数据测评结果表述为真实客户收益。
- 不将规划中的 Join、数据源接入、指标编辑和企业权限表述为已实现。
- 每次范围变更必须同步更新 PRD、路线图、需求池和评测方案。
- 质量结果必须注明样本量、运行环境和生成时间。
