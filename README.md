# DataPath

DataPath 是面向具备 SQL 基础的数据运营和数据分析师的可信 ChatBI Copilot。用户用自然语言提出业务问题，系统通过指标语义检索、结构化 Query DSL、确定性 SQL Compiler 和只读数仓执行返回表格、图表与可追溯解读。

> 当前基线：2026-07-13，作品集 MVP。项目没有真实客户、生产流量或业务收益数据，所有质量结论均来自本地 Olist 数据集和离线测评。

## 当前能力

- 原生 HTML/CSS/JavaScript 前端，包含问数工作台、指标口径、指标管理、Join 治理、质量运营和测评监控六个视图。
- FastAPI `/api/chatbi/ask` 作为浏览器入口，服务端串联上下文、检索、DSL、Compiler、ClickHouse、Profiler、Interpretation 和 Reflection。
- Olist Brazilian E-Commerce 九表数据，约 10 万订单。
- 12 个已发布指标，覆盖销售额、成交总额、订单量、客单价、运费、运费率、商品、卖家和购买客户等口径。
- Semantic Join Graph 与 Deterministic Join Planner，5 条安全关系已发布；支付和评价多事实关系仍为 `STAGED`。
- BM25 + `text-embedding-v3` + `qwen3-rerank` 的混合指标检索，结合完整名称优先、歧义澄清和能力边界拒绝。
- 会话级结构化 Memory，可继承上一轮指标、维度和时间范围并允许显式覆盖。
- 指标草稿、校验、不可变版本发布，以及 Join 关系草稿、检测和发布。
- Evidence、Reflection、Bad Case、黄金问题和回归测评闭环。

## 架构

```text
Browser
  -> FastAPI /api/chatbi/ask
  -> Context + Query Understanding
  -> Hybrid Metric Retrieval + Confidence Gate
  -> Query DSL 2.0 + Validator
  -> Semantic Join Graph + Deterministic Planner
  -> SQL Compiler
  -> ClickHouse read-only execution
  -> Result Profiler + Evidence
  -> Interpretation + Reflection
  -> Interactive result
```

PostgreSQL 保存指标、版本、语义资产、向量、Join Graph、查询审计、会话上下文、Evidence、反馈和黄金问题；ClickHouse 保存 Olist 事实与维度表；Redis 已作为本地基础设施预留，但当前主链不依赖 Redis 状态。

Dify Workflow DSL 保留为可选的内部 AI 编排交付物，不是浏览器入口，也不是数据权限或 SQL 安全边界。当前 `/api/chatbi/ask` 可独立完成端到端问数。

## 快速开始

要求：Python 3.12、Docker Desktop、`uv`。

```bash
cp .env.example .env
uv sync
docker compose up -d
uv run alembic upgrade head
```

首次准备 Olist 数据：

```bash
uv run python -m scripts.download_olist
uv run python -m scripts.load_olist
uv run python -m scripts.validate_olist
```

初始化语义资产：

```bash
uv run python -m scripts.seed_metric_center
uv run python -m scripts.rebuild_metric_vector_index
```

`rebuild_metric_vector_index` 需要在 `.env` 中配置阿里云百炼 `DASHSCOPE_API_KEY`。未配置或外部服务异常时，在线检索会降级到文本检索。

启动 Web 服务：

```bash
NO_PROXY=127.0.0.1,localhost uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)。

## 验证

```bash
uv run pytest
uv run python -m scripts.validate_contracts
NO_PROXY=127.0.0.1,localhost uv run python -m scripts.smoke_chatbi_api
```

重建 360 条 Olist 黄金集：

```bash
uv run python -m scripts.build_olist_golden_dataset
```

运行 80 条发布回归集：

```bash
uv run python -m scripts.evaluate_olist_golden_dataset --split regression \
  --report-name olist-expanded-metrics-regression
```

当前最新回归结果为 73/80（91.25%）。核心指标、多实体查询、多轮上下文、语义鲁棒性和数据边界在该回归切片中均为 100%；剩余 7 条集中在 `CLARIFY`、`REJECT` 与 `BLOCKED` 的状态标准差异。详见 [最新 Olist 回归报告](reports/olist-expanded-metrics-regression.md)。

## 数据与安全边界

- 当前只支持 Olist 数据域，不再使用旧 UCI 或模拟销售/广告数据作为产品主数据。
- 查询只允许已发布指标、已注册字段和已发布安全 Join Path。
- 支付和评价表尚未进入多事实查询；`aggregate-before-join` 仍是后续能力。
- 当前只有 `demo` 工作空间和公开演示身份，不具备企业级 SSO、RBAC、行列权限或多租户隔离。
- 不支持任意 SQL、DDL/DML、数据写回、完整因果归因和自由 Join。
- 仓库中的默认密码仅用于本地开发；生产环境必须使用密钥管理、网络隔离、审计和最小权限账号。

## 文档

- [产品文档中心](document/product/README.md)
- [项目理解报告](document/product/00-project-understanding.md)
- [产品需求文档](document/product/01-product-requirements.md)
- [AI 与可信架构](document/product/03-ai-capability.md)
- [Olist 数据与多表能力](document/product/09-olist-multitable-evaluation.md)
- [指标语义检索架构](document/product/12-semantic-retrieval-architecture.md)
- [Semantic Join Graph 治理](document/product/15-semantic-join-graph-governance.md)
- [当前指标目录](document/initial-metric-catalog.md)
- [Dify Workflow 导入手册](document/dify-chatbi-workflow-import.md)
- [OpenAPI 契约](document/chatbi-openapi.yaml)
- [Query DSL Schema](document/query-dsl-v1.schema.json)

## 许可证与数据来源

Olist 数据来源与本地使用边界见 [data/external/olist/README.md](data/external/olist/README.md)。项目代码当前未声明开源许可证；公开分发前需要补充仓库许可证并再次核对第三方数据条款。
