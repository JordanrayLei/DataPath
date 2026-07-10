# Reflection Validator 阶段验收

> 验收日期：2026-07-08
>
> 接口：`POST /api/chatbi/reflection/validate`

## 1. 实现内容

Reflection Validator 对 AI 解读执行确定性后置校验，并返回三种决策：

- `PASS`：结论均能由所引 Evidence 支持。
- `REVISE`：事实基础可用，但单位、时间、数据限制或因果表达需要修改。
- `BLOCK`：存在未知 Evidence、数字造假、指标版本冲突或敏感信息，禁止输出 AI 解读。

## 2. 信任边界

后端不信任 Dify 回传的 Profile 内容，只用 `query_id` 和 `profile_id` 定位服务端审计记录，并从以下表反查事实：

- `audit.query_run`
- `audit.result_profile`
- `audit.evidence`

请求 DSL 必须与编译时 DSL Hash 一致，Query 必须属于当前 Workspace 且状态为 `SUCCEEDED`。

## 3. 校验规则

当前实现覆盖：

- Evidence ID 是否属于本次 Query/Profile。
- 文本数字是否能与 Evidence 值、基线、变化额、变化率、占比或 z-score 对齐。
- 显式金额和百分比单位是否与证据口径一致。
- 文本日期是否落在 Evidence 时间范围内。
- Evidence 指标版本是否与 Query Run 快照一致。
- 关键数据质量限制是否在解读 Caveat 中保留。
- 描述性 Evidence 是否被越界写成因果结论。
- 手机号、邮箱、身份证、凭据或原始 SQL 等敏感内容是否暴露。

## 4. 审计与幂等

新增 Alembic Revision：`28df3bb0422e_add_reflection_validations.py`。

新增 `audit.reflection_validation`，保存 Interpretation Hash、Profile ID、决策、问题列表和修订指令。同一 Query 与同一 Interpretation 重复校验时直接返回已保存结果，不重复写入。

## 5. 测试结果

自动化集成测试覆盖：

- 直接引用服务端 Evidence Statement：`PASS`。
- 将描述性变化写成“导致业务增长”：`REVISE`，问题码为 `UNSUPPORTED_CAUSAL_CLAIM`。
- 将 GMV 篡改为 `999999999 CNY`：`BLOCK`，问题码为 `NUMERIC_MISMATCH`。
- 引用不存在的 Evidence ID：`BLOCK`。
- 相同 Interpretation 重复请求保持幂等。

真实 Uvicorn HTTP smoke 期望输出：

```text
PASS: reflection/validate (Evidence-bound interpretation)
```

## 6. 已知边界

- 数字校验使用确定性容差和文本规则，不承担通用自然语言数学证明。
- 当前因果判断采用高风险词规则，没有实验设计或因果推断模型。
- Dify 的 Revision 节点修订后尚未二次调用 Reflection。
- Dify 画布尚未完成导入、发布、Human Input 和完整 E2E。

## 7. 验收结论

7 个 ChatBI 后端契约接口均已实现，查询结果到 Evidence 再到 Reflection 的服务端闭环成立。当前可以声称“后端垂直链路真实跑通”，但不能声称“Dify 端到端生产系统已完成”。
