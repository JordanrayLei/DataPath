# Dify Workflow 导入与联调手册

> 适用资产：`document/dify-chatbi-workflow.zh-CN.dsl.yml`
> 更新日期：2026-07-13
> 定位：可选内部编排资产，不是 DataPath 浏览器主入口

## 1. 使用边界

DataPath 当前 `/api/chatbi/ask` 由 FastAPI BFF 直接编排完整可信链路，运行产品不要求部署 Dify。Dify DSL 用于：

- 展示 LLM 预处理、候选消歧、DSL 草稿和修订分支。
- 验证内部 ChatBI API 的工作流编排能力。
- 作为项目交付时可导入的 AI Workflow 资产。

Dify 不负责最终权限、指标发布状态、SQL 安全、数仓凭证或 Evidence 校验。

## 2. 资产与依赖

当前 DSL 包含 53 个节点、58 条边，调用八个受保护的 `/api/chatbi/*` 内部接口。导入前需要：

1. 可创建 Workflow 的 Dify 工作空间。
2. 可用 Chat Model Provider；DSL 当前模型节点使用 DeepSeek Chat，可在导入后替换。
3. Dify 环境能够访问运行中的 FastAPI。
4. PostgreSQL、ClickHouse 和 DataPath 语义资产已初始化。

## 3. 启动后端

```bash
docker compose up -d
uv run alembic upgrade head
uv run python -m scripts.seed_metric_center
NO_PROXY=127.0.0.1,localhost uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

先验证内部契约：

```bash
uv run python -m scripts.validate_contracts
NO_PROXY=127.0.0.1,localhost uv run python -m scripts.smoke_chatbi_api
```

## 4. Dify 环境变量

本地 Docker 中的 Dify：

```text
CHATBI_API_BASE_URL=http://host.docker.internal:8000/api/chatbi
CHATBI_API_TOKEN=<与 .env 中 CHATBI_API_TOKEN 相同>
```

DSL 可通过文件导入，也可使用本地只读导出地址：

```text
http://host.docker.internal:8000/portfolio/dify-chatbi-workflow.dsl.yml
```

Secret 必须配置在 Dify 环境变量中，不能写入 DSL 或提交 Git。

## 5. 导入步骤

1. 在 Dify 创建 Workflow 应用并导入 DSL。
2. 确认画布有 53 个节点、58 条边。
3. 为模型节点选择已配置的 Chat Model。
4. 配置 `CHATBI_API_BASE_URL` 与 `CHATBI_API_TOKEN`。
5. 检查所有 HTTP 节点携带 Request ID、Trace ID 和 Bearer Token。
6. 确认 Execute 节点传递 `execution_token`，不传 SQL 文本。

## 6. 推荐测试

成功用例：

```text
query=2018年前九个月每月Olist成交总额趋势
workspace_id=demo
biz_domain=sales
conversation_id=dify-e2e-001
timezone=Asia/Shanghai
identity_token=<DEMO_IDENTITY_TOKEN>
```

还应验证：

- 指标歧义进入澄清，不执行 SQL。
- 未支持指标进入拒绝。
- 非 demo 工作空间被阻断。
- Execute/Profile/Reflection 任一失败时 fail-closed。
- Reflection `REVISE` 只允许受 Evidence 约束的二次修订。

## 7. Dify Cloud

Dify Cloud 无法访问本机地址。只有在明确接受临时公网暴露风险时，才能将 FastAPI 部署到 HTTPS 地址或使用短时 Tunnel。不得暴露 PostgreSQL、ClickHouse、Redis 或内部管理端口。

Cloud 联调不是当前产品运行的必要条件，也不能替代本地 API、权限和回归测试。

## 8. 已知差距

- 当前在线 BFF 与 Dify DSL 是两套编排路径，需要定期做契约一致性检查。
- Prompt 没有 Registry、版本发布或评测关联。
- DSL 仍包含历史通用流程设计，新增 12 指标和 Join Graph 后应持续验证节点输出兼容性。
- Dify E2E 的模型稳定性、成本和延迟不纳入当前 91.25% Olist 发布回归结论。
