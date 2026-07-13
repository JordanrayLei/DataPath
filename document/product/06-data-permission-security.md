# DataPath 数据、权限与安全说明

> 更新日期：2026-07-13

## 1. 数据分类

| 数据 | 当前存储 | 说明 |
| --- | --- | --- |
| Olist 事实与维度 | ClickHouse | 公开匿名电商数据，不含企业生产数据 |
| 指标与版本 | PostgreSQL `metric_center` | 定义、公式、维度、血缘和状态 |
| 语义向量 | PostgreSQL + pgvector | 指标文档与能力边界样本 |
| Join Graph | PostgreSQL `metric_center` | 实体、关系、验证结果和版本 |
| 查询审计 | PostgreSQL | DSL、SQL、参数、Fingerprint、血缘和状态 |
| 会话上下文 | PostgreSQL | 最近成功查询的结构化上下文 |
| Evidence/Reflection | PostgreSQL | 结果证据和可信校验 |
| 反馈与黄金问题 | PostgreSQL / JSON | 质量运营资产 |

## 2. 当前身份与权限

- 浏览器只访问 `/api/chatbi/ask` 等产品 BFF，不持有内部 service token。
- 内部八个 ChatBI 接口要求 Bearer Token。
- 当前只允许 `demo` 工作空间和 `public_demo_user`。
- 非 demo 工作空间在上下文/策略层被阻断。
- `row_policy_token` 已进入上下文契约，但没有真实企业行级策略引擎。

当前实现不能对外宣称具备企业级 ACL-aware Retrieval、RBAC 或多租户隔离。

## 3. 查询安全

- 指标和版本必须已发布。
- 维度与字段必须在语义模型映射和白名单中。
- Join 只能来自已发布、安全的 Semantic Join Relation。
- SQL 由服务端生成，参数化执行，设置 Limit 和最长时间范围。
- Compiler 与执行账号分离，执行使用签名 Token 和 SQL Fingerprint。
- ClickHouse 使用只读查询链路，不支持 DDL、DML 或写回。
- API 不向产品响应泄露完整 SQL；用户查看 SQL 通过受控交互获取。

## 4. AI 安全

- LLM 或 Reranker 不能绕过指标发布、权限、DSL 和 Join 门禁。
- 数字必须来自 Tool 返回结果或 Evidence。
- Reflection 校验指标版本、单位、时间、数字、敏感字段和因果表达。
- 外部 AI 服务异常时降级，不扩大权限或自由生成 SQL。

## 5. 当前缺口

- SSO、组织、角色、数据源级权限。
- 行列权限、敏感字段标签、动态脱敏。
- 用户和指标的 ACL-aware Retrieval。
- 密钥管理系统、凭证轮换和数据源连接审计。
- 多租户存储隔离、配额、限流和成本控制。
- 完整安全事件监控、告警和审计导出。

## 6. 生产接入要求

真实数据源接入前必须完成：

1. 只读凭证与网络白名单。
2. 数据分类分级和敏感字段扫描。
3. 用户、工作空间、角色与数据范围映射。
4. Schema/指标/Join 发布审批。
5. 查询审计、限流、超时、成本预估和异常告警。
6. 密钥托管、备份、恢复和数据保留策略。

## 7. 数据集边界

Olist 数据是公开匿名样本，适合验证电商多表查询，但不能证明企业数据合规、权限隔离或生产性能。公开展示时应保留来源说明，不上传被忽略的原始 CSV，除非许可证与分发条款再次确认。
