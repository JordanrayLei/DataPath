# DataPath 需求池与迭代管理

> 更新日期：2026-07-13

## 状态定义

`BACKLOG` -> `READY` -> `IN_PROGRESS` -> `VALIDATING` -> `DONE`

任何规划能力只有在代码、测试和文档均完成后才能标记 `DONE`。

## 当前需求池

| ID | 需求 | 优先级 | 状态 | 完成出口 |
| --- | --- | --- | --- | --- |
| Q-01 | 统一 CLARIFY/REJECT/BLOCKED | P0 | READY | 7 条回归 Bad Case 关闭 |
| Q-02 | 安全动作意图前置识别 | P0 | BACKLOG | DDL/DML/敏感导出稳定 BLOCKED |
| G-01 | 指标提交、审核和驳回 | P1 | BACKLOG | 未审核版本不进入检索 |
| G-02 | 指标废弃与生效时间 | P1 | BACKLOG | 历史查询仍可追溯旧版本 |
| G-03 | 指标变更影响分析 | P1 | BACKLOG | 展示受影响黄金问题、查询和血缘 |
| J-01 | Join Graph 状态可视化 | P1 | BACKLOG | 发布/草稿/暂存关系一眼可区分 |
| J-02 | 元数据同步任务 | P1 | BACKLOG | 定时 Schema Diff 并生成候选 |
| J-03 | Aggregate-Before-Join | P1 | BACKLOG | 支付和评价指标通过独立 Oracle |
| D-01 | 数据源连接管理 | P1 | BACKLOG | 用户可配置并测试只读连接 |
| D-02 | Schema 扫描与模型映射 | P1 | BACKLOG | 新表字段生成待审核语义候选 |
| E-01 | 私有盲测与版本对比 | P1 | BACKLOG | 报告关联 Commit/指标/模型/数据版本 |
| S-01 | SSO/RBAC/行列权限 | P2 | BACKLOG | 权限在检索和执行前生效 |
| O-01 | 监控、限流和成本 | P2 | BACKLOG | 有 P95、错误率、外部模型成本告警 |

## 已完成能力

- 12 个指标的创建、校验和版本发布。
- 5 条安全 Join Relation 的治理和发布。
- Hybrid Retrieval、Embedding、Reranker 和完整名称优先。
- 多轮上下文继承。
- 360 条黄金集与 80 条发布回归。
- Olist 多表查询、Evidence 和 Reflection。

## Definition of Ready

- 明确用户、业务问题、成功指标和非目标。
- 有数据源、指标、维度、权限和错误边界。
- 有可独立验证的黄金用例或测试方案。
- 已确认对现有指标、Join、DSL 和前端的影响。

## Definition of Done

- 代码、迁移、种子数据和接口契约完成。
- 正向、歧义、拒绝、权限和错误测试完成。
- 自动测试与发布回归无新增失败。
- 产品文档、运行手册和 Bad Case 状态同步。
- 运行环境可复现，规划项未被误写为已实现。
