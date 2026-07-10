# ChatBI 前五接口阶段验收

> 验收日期：2026-07-07
>
> 范围：Context、Metric Retrieval、DSL Validator、Query Compiler、Warehouse Execute

## 1. 实现范围

已实现：

```text
POST /api/chatbi/context/load
POST /api/chatbi/metrics/retrieve
POST /api/chatbi/dsl/validate
POST /api/chatbi/query/compile
POST /api/chatbi/query/execute
```

尚未实现：

```text
POST /api/chatbi/result/profile
POST /api/chatbi/reflection/validate
```

## 2. 控制平面

PostgreSQL 已通过 Alembic 正式 Revision 创建：

- `metric_center.business_domain`
- `metric_center.semantic_model`
- `metric_center.dimension`
- `metric_center.metric`
- `metric_center.metric_version`
- `metric_center.metric_alias`
- `metric_center.metric_dimension`
- `app.conversation_context`
- `audit.query_run`

迁移：`5bec1957b97f_create_control_plane.py`。

`alembic check` 结果：`No new upgrade operations detected.`

种子数据：

- 2 个业务域。
- 2 个语义模型。
- 12 个维度。
- 6 个已发布指标及不可变版本。

## 3. 安全边界

### 3.1 SQL 生成

- Query DSL 不包含物理表和 SQL。
- 指标公式使用受限 AST：`sum`、`count_distinct`、`ratio`。
- Compiler 使用表和字段白名单。
- 筛选值使用 ClickHouse HTTP 参数，不拼接用户原文。

### 3.2 SQL 存储与执行

- 编译响应不返回 SQL 正文。
- SQL 仅保存在 `audit.query_run`。
- Executor 根据 `query_id` 加载服务端 SQL。
- Dify 兼容字段 `compiled_query` 被明确忽略。
- Query ID 同时作为 Idempotency-Key。

### 3.3 账号分离

- Compiler 使用管理账号读取 `system.parts` 做基础成本预估。
- Executor 使用 `chatbi_reader` 只读账号查询业务表。
- 未通过扩大只读账号权限解决成本预估问题。

### 3.4 执行 Token

- Compiler 返回 HMAC 执行 Token。
- Token 绑定 Query ID、SQL Fingerprint 和过期时间。
- 过期时间以 Unix 时间戳签名，避免 PostgreSQL 时区显示差异导致误拒绝。

## 4. 接口行为

### Context

- 校验服务 Bearer Token。
- 校验演示身份 Token 和 Workspace。
- 返回固定公开演示用户、允许业务域、不透明策略 Token 和上一轮上下文。

### Metric Retrieval

- 仅检索已发布指标。
- 支持正式名称和别名匹配。
- “毛利”返回 `CLARIFY`，候选为毛利额和毛利率。
- “毛利率”和“GMV”等精确表达返回 `PASS`。
- 当前分数是确定性启发式基线，不是已校准生产概率。

### DSL Validator

- 校验 JSON 结构、指标版本、发布状态、业务域、维度兼容性。
- 校验筛选字段、操作符、排序字段和最大时间范围。
- MVP 拒绝跨语义模型查询和聚合方式覆盖。

### Query Compiler

- 从指标 AST 和维度映射确定性生成 ClickHouse SQL。
- 对比率显式使用 `Float64`，避免 Decimal 除法精度丢失。
- 生成 Query ID、DSL Hash、SQL Fingerprint、血缘、成本和执行 Token。
- 不向 Dify 返回 SQL 正文。

### Query Execute

- 验证 Workspace、Operator、Query ID、状态、过期时间和可选执行 Token。
- 使用只读 ClickHouse 账号。
- 重复执行返回已保存结果并标记 `cached=true`。
- 请求中的恶意 `compiled_query` 不影响执行内容。

## 5. 自动测试

集成测试结果：

```text
5 passed
```

覆盖：

1. 缺少服务 Token 返回 401。
2. Context 返回演示权限上下文。
3. “毛利”澄清与“毛利率”精确通过。
4. 未知指标版本被 Validator 拒绝。
5. Validate → Compile → Execute 真实闭环。
6. 编译响应不包含 SQL。
7. 恶意 `compiled_query` 被忽略。
8. 重复执行命中幂等结果。

真实 Uvicorn 网络 smoke：

```text
PASS: context/load
PASS: metrics/retrieve
PASS: dsl/validate
PASS: query/compile (SQL not exposed)
PASS: query/execute (12 rows; request SQL ignored)
```

## 6. 数据结果

HTTP smoke 查询：2025-07-01 至 2026-06-30 每月 GMV。

- 返回 12 行月度数据。
- SQL 未出现在编译响应。
- 查询由只读 ClickHouse 账号执行。
- Query Run、Fingerprint、参数和结果已保存到 PostgreSQL。

## 7. 已知边界

- 当前只发布 6 个可执行指标，其余 18 个仍是产品目录定义。
- 指标检索是名称、别名和字符串相似度基线，尚无 BM25/Dense/Reranker 和概率校准。
- 当前公开演示用户可访问两个业务域，尚无企业 SSO、RBAC 和行列权限。
- 成本预估当前使用表活动分区行数，不是完整 EXPLAIN 成本模型。
- 暂不支持跨语义模型查询、高风险审批和大结果 `result_ref`。
- Profiler、Evidence、Reflection 和 Dify 画布联调尚未完成。

## 8. 验收结论

前五接口最小垂直链已真实跑通，达到进入结果画像与 Evidence 开发的条件。但不能描述为 Dify ChatBI 全链完成；目前尚缺后两接口及 Dify 状态机修复、导入和端到端联调。
