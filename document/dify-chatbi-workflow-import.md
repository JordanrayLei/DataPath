# Dify Workflow 导入与 E2E 操作手册

> 适用文件：`dify-chatbi-workflow.zh-CN.dsl.yml`
>
> 当前结构：53 个节点、58 条边、9 个 HTTP 节点、9 个 Code 节点、12 个终态节点。

## 1. 导入前准备

需要准备：

1. 一个可创建 Workflow 应用的 Dify 工作空间。
2. 已安装并配置的 Chat Model Provider。
3. Dify 运行环境能够访问 ChatBI API。
4. ChatBI 后端已运行，PostgreSQL 和 ClickHouse 数据底座健康。

4 个模型节点已统一配置为 `langgenius/deepseek/deepseek / deepseek-chat`。导入前需要在 Dify Cloud 工作空间安装 DeepSeek 官方 Model Provider，并由项目所有者在 Dify 中配置 DeepSeek API Key：

- `preprocess_llm`
- `disambiguate_llm`
- `dsl_llm`
- `revision_llm`

主链路业务解读不再依赖 LLM 节点，改为调用后端：

```text
POST {{CHATBI_API_BASE_URL}}/interpretation/generate
```

该接口从服务端 Evidence 生成确定性 Interpretation，再进入 Reflection 校验。这样本地演示不会因为外部 LLM 插件流式断连而中断。

## 2. 网络地址选择

### Dify 与后端都在本机 Docker

环境变量可使用：

```text
CHATBI_API_BASE_URL=http://host.docker.internal:8000/api/chatbi
```

本地 FastAPI 同时提供一个只读 DSL 导出端点，便于在 Dify 的“URL 导入”中使用：

```text
http://host.docker.internal:8000/portfolio/dify-chatbi-workflow.dsl.yml
```

该端点只返回 `document/dify-chatbi-workflow.zh-CN.dsl.yml` 文件内容，不包含真实 Secret。

### Dify Cloud

Dify Cloud 无法访问 `127.0.0.1` 或 `host.docker.internal`。必须先把 ChatBI API 部署到可由 Dify Cloud 访问的 HTTPS 地址，再填写：

```text
CHATBI_API_BASE_URL=https://your-domain.example/api/chatbi
```

不要把 PostgreSQL、ClickHouse 或内部管理端口暴露到公网。

本地作品集联调可使用临时 Cloudflare Quick Tunnel。仓库提供了三个 PowerShell 脚本：

```powershell
# 1. 生成不使用默认值的本地演示密钥
.\scripts\prepare_dify_cloud_demo.ps1

# 2. 重启 FastAPI，使其加载 .env 并关闭公网演示环境的 API 文档
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. 预检通过后，显式确认并启动临时 HTTPS Tunnel
.\scripts\start_dify_cloud_tunnel.ps1 -ConfirmTemporaryPublicExposure
```

Quick Tunnel URL 只在进程运行期间有效，按 `Ctrl+C` 后失效。它只适合临时联调，不用于生产部署。

## 3. 导入步骤

1. 在 Dify 选择“创建应用”。
2. 选择“导入 DSL 文件”。
3. 上传 `document/dify-chatbi-workflow.zh-CN.dsl.yml`。
   - 本地 Docker 场景也可以切到 URL 导入，填写 `http://host.docker.internal:8000/portfolio/dify-chatbi-workflow.dsl.yml`。
4. 打开画布，确认显示 53 个节点、58 条边。
5. 检查 4 个 LLM 节点均使用 `deepseek-chat`，并确认 DeepSeek Provider 凭证有效。
6. 在环境变量中配置：

```text
CHATBI_API_BASE_URL=<Dify 可访问的后端地址>
CHATBI_API_TOKEN=<与后端 CHATBI_API_TOKEN 一致的服务令牌>
```

令牌应直接在 Dify Secret 环境变量中填写，不要写回 DSL 或提交到仓库。

首次测试时，Start 节点的 `identity_token` 应填写本机 `.env` 中的 `DEMO_IDENTITY_TOKEN`，不要继续使用文档里的默认示例值。

## 4. 必查安全链

导入后在画布确认以下路径没有被 Dify 自动丢失：

```text
context_parse → context_gate → preprocess_llm / context_error_end
execute_http → execute_parse → execute_gate → profile_http / execute_failed_end
profile_parse → profile_gate → interpret_http → interpret_parse → reflection_http / profile_failed_end
revision_llm → revision_reflection_http → revision_reflection_parse
             → revision_reflection_gate → revision_template / revision_data_only_template
```

所有 HTTP 节点应携带：

```text
X-Request-ID: {{#sys.workflow_run_id#}}
X-Trace-ID: {{#sys.workflow_run_id#}}
```

Execute 请求必须发送 `execution_token`，不得发送 SQL 或 `compiled_query`。

## 5. 首次成功用例

输入：

```text
query=最近一年每月 GMV
workspace_id=demo
biz_domain=sales
conversation_id=dify-e2e-001
timezone=Asia/Shanghai
identity_token=demo-server-issued-token
```

预期路径：

```text
Context PASS
→ Metric Retrieval PASS
→ DSL VALID
→ Compile READY
→ Execute SUCCEEDED
→ Profile PASS
→ Deterministic Interpretation PASS
→ Reflection PASS 或 REVISE
→ SUCCESS 或经二次 Reflection 后 REVISED
```

## 6. 必测失败分支

| 场景 | 操作 | 预期 |
| --- | --- | --- |
| Context 失败 | 使用错误 `identity_token` | `context_error_end` |
| 指标拒绝 | 输入无法识别的指标 | `reject_end` |
| DSL 无效 | 让 DSL 使用未发布指标或非法时间 | `dsl_deny_end` |
| Execute 凭证缺失 | 临时清空 Execute 的 `execution_token` | `execute_failed_end` |
| Profile 失败 | 临时配置错误 Profile URL | `profile_failed_end` |
| Reflection BLOCK | 构造未知 Evidence 或篡改数字 | `data_only_end` |
| 修订仍失败 | Revision 保留因果越界或错误数字 | `revision_data_only_end` |

完成故障测试后恢复正确配置，不要发布故障注入版本。

## 7. 当前仍未完成的生产能力

- 指标澄清 Human Input 只提供两个候选按钮，尚未可靠绑定完整 `metric_id + metric_version`。
- 高风险查询审批尚无服务端 Approval API 和签名 `approval_token`；当前后端只产生 `READY` 查询。
- 大结果 `result_ref`、取消接口和对象存储尚未实现。
- 12 个 End 节点的输出 Envelope 尚未统一。
- 当前身份和服务令牌仅适合本地作品集演示。

## 8. 需要项目所有者提供的信息

进入真实导入阶段时，只需确认：

1. Dify Cloud 工作空间是否已安装并配置 DeepSeek Provider。
2. 是否批准为作品集联调临时创建一个只转发 `127.0.0.1:8000` 的 HTTPS Quick Tunnel。
3. 若不使用临时 Tunnel，需要提供一个可部署后端的测试服务器或域名。

不要在聊天中发送真实 API Key、模型密钥或生产令牌；这些凭据应由项目所有者直接填入 Dify Secret 配置。
