# AI 数据运营平台

一个面向业务运营的通用 ChatBI 作品集：自然语言问题经过指标解析、Query DSL、确定性 SQL 编译和安全执行后，返回可追溯的数据、图表和业务解读。

## 当前状态

- 已有 53 节点、58 条边的可导入 Dify Workflow DSL，关键错误分支已改为 fail-closed，主链路业务解读已切换为后端 Evidence fallback。
- 已完成 PRD、24 个首发指标、Query DSL 1.0 和 8 个 ChatBI API 契约。
- 已完成 PostgreSQL、ClickHouse、Redis 的本地数据底座配置。
- 已完成电商和广告可复现演示数据、ODS/DWD/DWS 模型和 6 个指标基准校验。
- 8 个 `/api/chatbi/*` 后端接口已全部实现并通过真实 HTTP smoke。
- Result Profiler 已提供强类型 Evidence，Reflection Validator 已实现 PASS/REVISE/BLOCK；新增确定性业务解读 fallback，可在 Dify LLM 插件不稳定时兜底。当前 Dify 端到端已打通到数仓执行和画像，待把业务解读节点切换为 fallback 后完成稳定演示闭环。
- 已新增产品前端入口，由 FastAPI 直接托管 `/` 和 `/app` 页面；浏览器调用 `/api/chatbi/ask`，服务端完成完整 ChatBI 链路并保护内部 service token。

## 快速开始

```powershell
Copy-Item .env.example .env
docker compose up -d
```

生成轻量 smoke 数据：

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --profile smoke
.\.venv\Scripts\python.exe scripts\validate_generated_data.py
```

加载 ClickHouse 并验证指标：

```powershell
.\.venv\Scripts\python.exe scripts\load_clickhouse_data.py
.\.venv\Scripts\python.exe scripts\verify_clickhouse_metrics.py
```

初始化指标中心并启动 API：

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m scripts.seed_metric_center
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开产品前端入口：

```text
http://127.0.0.1:8000/
```

前端入口会调用：

```text
POST /api/chatbi/ask
```

该接口用于产品 UI，不需要浏览器携带内部 service token；原有 8 个 `/api/chatbi/*` 内部接口仍保留 Bearer Token 保护。

本地 Dify Docker 可通过以下只读地址导入当前 Workflow DSL：

```text
http://host.docker.internal:8000/portfolio/dify-chatbi-workflow.dsl.yml
```

另开一个终端执行真实 HTTP smoke：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_chatbi_api.py
```

执行产品入口测评：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_chatbi_entrypoint.py
```

测评会覆盖：

- 成功链路：自然语言到可信解读闭环。
- 排行链路：非时间维度聚合与柱状图展示。
- 歧义链路：指标口径不清时安全澄清，不执行查询。
- 拒绝链路：未知指标不生成 DSL、不编译查询。
- 权限链路：非 demo workspace 被拦截。
- 安全门禁：内部服务接口仍要求 Bearer Token。
- 反馈门禁：成功查询可提交 Badcase 反馈，并进入回归集候选。
- 看板门禁：Badcase 能在看板出现，并推进到 `CONFIRMED` 状态。
- 黄金集门禁：已确认 Badcase 能沉淀为黄金问题，并通过回归评测。
- 指标口径门禁：指标目录能返回口径、公式、维度和数仓血缘。
- 测评看板：前端可读取最新评测报告，展示通过率、用例结果和安全/可信门禁。
- 测评趋势：每次生成报告时会沉淀历史快照，前端展示通过率、失败门禁和平均耗时的时间变化。

默认输出：

```text
reports/chatbi-entrypoint-evaluation-latest.json
reports/chatbi-entrypoint-evaluation-latest.md
reports/evaluation-history/<report-name>-<generated-at>.json
```

对真实运行中的服务执行测评：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_chatbi_entrypoint.py --base-url http://127.0.0.1:8000
```

Dify Cloud 临时联调前，先阅读导入手册并生成独立演示密钥：

```powershell
.\scripts\prepare_dify_cloud_demo.ps1
```

运行集成测试：

```powershell
.\.venv\Scripts\pytest.exe
```

校验产品契约：

```powershell
.\.venv\Scripts\python.exe scripts\validate_contracts.py
```

## 数据规模档位

| Profile | 订单数 | 用途 |
| --- | ---: | --- |
| `smoke` | 5,000 | 快速开发和 CI |
| `demo` | 100,000 | 日常产品演示 |
| `portfolio` | 600,000 | 生成约百万级订单明细，用于性能展示 |

## 文档入口

- [产品 PRD](document/ai-data-operations-platform-prd.md)
- [执行方案](document/ai-data-operations-platform-execution-plan.md)
- [首发指标目录](document/initial-metric-catalog.md)
- [数据底座说明](document/data-foundation.md)
- [数据底座验收记录](document/data-foundation-acceptance.md)
- [ChatBI 后端阶段验收](document/chatbi-backend-phase-acceptance.md)
- [Result Profiler 阶段验收](document/result-profiler-phase-acceptance.md)
- [Reflection Validator 阶段验收](document/reflection-validator-phase-acceptance.md)
- [Dify 完整上下文](document/dify-chatbi-complete-ai-context.md)
- [Dify Workflow 导入与 E2E 手册](document/dify-chatbi-workflow-import.md)
- [Dify 本地端到端联调记录 2026-07-09](document/dify-local-e2e-2026-07-09.md)
- [Dify 安全编排阶段验收](document/dify-safety-workflow-phase-acceptance.md)
- [ChatBI OpenAPI](document/chatbi-openapi.yaml)
- [ChatBI 产品入口测评报告](reports/chatbi-entrypoint-evaluation-latest.md)
- [作品集一页总览](document/portfolio-one-page-overview.md)
- [产品决策说明](document/product-decision-rationale.md)
- [作品集演示脚本](document/portfolio-demo-script.md)

## 安全说明

仓库内密码只用于本地公开演示环境。生产部署必须使用密钥管理、只读执行账号、网络隔离、SSO/RBAC、行列权限和审计，不得复用示例凭证。
