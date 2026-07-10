# Dify 安全编排阶段验收

> 验收日期：2026-07-08
>
> DSL：`dify-chatbi-workflow.zh-CN.dsl.yml`

## 完成内容

- Workflow 从 40 节点、45 条边扩展为 52 节点、57 条边。
- Context 加入 fail-closed 门控，身份或上下文失败立即终止。
- 8 个 HTTP 节点使用 `sys.workflow_run_id` 透传 Request ID 和 Trace ID。
- Compiler 输出的签名 `execution_token` 已传入 Execute。
- Execute 不再接收 `compiled_query`，后端同时改为强制校验 Execution Token。
- Execute 加入响应解析与 `SUCCEEDED` 门控。
- Profile 加入 `profile_ok` 门控，失败不进入 LLM。
- Revision 后加入第二次 Reflection，非 `PASS` 统一降级 Data-only。
- 二次 Reflection 失败使用独立 Template 和 End，保留真实二次校验结果。

2026-07-09 增量：

- Workflow 扩展为 53 节点、58 条边。
- HTTP 节点从 8 个增加到 9 个，Code 节点从 8 个增加到 9 个。
- 主链路 `interpret_llm` 已替换为 `interpret_http → interpret_parse`，调用 `/api/chatbi/interpretation/generate` 生成确定性 Evidence-bound Interpretation。
- LLM 节点从 5 个降为 4 个，主链路不再因业务解读 LLM 插件断流而中断。

## 自动校验

`scripts/validate_contracts.py` 现在检查：

- 关键安全节点和边存在。
- 原有四条危险直连边不存在。
- 节点 ID 和边唯一。
- 所有边引用有效节点。
- 所有 53 个节点从 Start 可达。
- 非 End 节点都有出边，End 节点没有出边。
- 9 个 Code 节点均可编译。
- 模板不存在未知节点引用。
- 所有 HTTP 节点透传 Request ID 和 Trace ID。
- Execute 发送 `execution_token` 且不发送 `compiled_query`。
- `interpret_http` 发送 Profile/Evidence，`reflection_http` 校验 `interpret_parse.interpretation_json`。
- 二次 Reflection 校验 Revision 输出。

校验结果：

```text
PASS: Dify HTTP endpoint alignment
PASS: Dify fail-closed safety flow
```

## 后端回归

- Pytest：`6 passed`。
- Alembic：无模型漂移。
- 真实 HTTP smoke：8 个接口全部通过。
- Execute 缺少 Execution Token 时返回 409。

## 尚待真实 Dify 验证

- DSL 在目标 Dify 版本中的导入兼容性。
- 4 个 LLM 节点已统一为 `deepseek-chat`，仍需验证 Dify Cloud Provider 和凭证。
- Human Input 的暂停、恢复和动作变量。
- Dify 到本机或测试环境后端的网络可达性。
- PASS、REVISE、BLOCK、执行失败和画像失败的画布运行记录。

## 验收结论

本地 DSL 已达到“可进入真实 Dify 导入联调”的条件，但尚不能声称 Dify E2E 完成。下一阶段需要项目所有者提供 Dify 环境类型、访问入口和可用模型信息。
