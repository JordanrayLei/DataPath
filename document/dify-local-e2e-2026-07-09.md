# Dify 本地端到端联调记录

> 日期：2026-07-09  
> Dify：本地 Docker，`http://127.0.0.1:8080`  
> ChatBI API：本地 FastAPI，`http://127.0.0.1:8000/api/chatbi`

## 已完成

1. Dify 本地应用已能通过 `host.docker.internal:8000` 调用 ChatBI API。
2. `/metrics/retrieve` 已返回 `time_resolution` 和 `dsl_generation_constraints`，用于约束 Dify DSL 解析器处理相对时间。
3. “最近一年每月 GMV”不再解析到无数据的 `2023-04-01 ~ 2024-03-31`，已解析为样例数仓可用窗口：
   - `time_range.start = 2025-07-01`
   - `time_range.end = 2026-06-30`
   - `dimension_id = D_MONTH`
4. Dify 工作流已走到后端数仓执行和结果画像：
   - 最新 Dify QueryRun：`Q202607090114320A72F8B548`
   - 状态：`SUCCEEDED`
   - 返回行数：`12`
   - Evidence：`3` 条
5. 后端新增稳定兜底接口：
   - `POST /api/chatbi/interpretation/generate`
   - 作用：从服务端 Evidence 生成确定性 Interpretation，再交给 Reflection 校验。
6. 可导入 Dify DSL 已切换为 fallback 主链路：
   - `profile_gate → interpret_http → interpret_parse → reflection_http`
   - 当前结构：`53` 个节点、`58` 条边。
7. 本地 FastAPI 新增只读 DSL 导出端点：
   - `GET /portfolio/dify-chatbi-workflow.dsl.yml`
   - Dify Docker URL 导入地址：`http://host.docker.internal:8000/portfolio/dify-chatbi-workflow.dsl.yml`
8. 已通过 Dify URL 导入创建并发布新应用：
   - App ID：`1e45c563-d6c7-4cb2-9686-c0726d5bd0cf`
   - 运行页：`http://127.0.0.1:8080/workflow/clZfFk8HRtvaGSCE`
   - 测试运行状态：`SUCCESS`
   - 最新 Query ID：`Q202607090604228887EB7FD5`
   - 新链路已确认：`profile_gate → interpret_http → interpret_parse → reflection_http`
9. 旧应用已保留为历史版本并改名，避免演示时误点：
   - 旧 App ID：`002d63ec-2b62-4dc2-b13b-2e77195dd1e4`
   - 当前名称：`旧版-勿用 - ChatBI AI 编排器`
   - 旧链路特征：仍包含 `profile_gate → interpret_llm`

## 已定位的 live 应用阻塞

Dify 工作流在 `interpret_llm` 节点失败，Dify worker 日志确认：

```text
Node interpret_llm failed with ABORT strategy:
PluginInvokeError: {"error_type":"ChunkedEncodingError","message":"Response ended prematurely"}
```

这表示 DeepSeek/Dify 插件流式响应提前中断。失败发生在：

```text
result/profile 成功 → interpret_llm 失败 → reflection/validate 未执行
```

因此后端数据链路不是失败原因。

源码 DSL 已完成修复。旧应用已保留并标记为 `旧版-勿用 - ChatBI AI 编排器`；当前已通过 Dify URL 导入创建新应用并发布成功，后续联调优先使用 App ID `1e45c563-d6c7-4cb2-9686-c0726d5bd0cf`。

## 已验证命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.smoke_chatbi_api
.\.venv\Scripts\python.exe scripts\validate_contracts.py
```

期望 smoke 输出包含：

```text
PASS: interpretation/generate (deterministic Evidence-bound fallback)
PASS: reflection/validate (Evidence-bound interpretation)
```

## 下一步建议

下一步建议沉淀作品集演示脚本：

1. 明确只使用新版 App：`1e45c563-d6c7-4cb2-9686-c0726d5bd0cf`。
2. 准备 2-3 个标准演示问题，例如“最近一年每月 GMV 趋势如何？”。
3. 记录一条成功运行的输入、Query ID、关键节点链路和最终输出，用于作品集答辩。
4. 说明旧 App 的失败原因与修复策略，体现问题定位和生产化兜底设计能力。
