# DataPath AI 能力与可信架构

> 目的：统一 AI 能力边界、架构术语和对外表述

## 1. 能力定位

DataPath 是可信 ChatBI Copilot，采用 Agentic Workflow 完成受控问数。系统具备多步骤编排、工具调用、条件分支、人工澄清、失败重试思路和降级能力，但不属于多 Agent 自治系统。

## 2. AI 与确定性服务分工

| 能力 | 主要承担者 | 原则 |
| --- | --- | --- |
| 查询预处理 | DeepSeek Chat / 规则 | 提取业务表达，不决定最终口径 |
| 指标检索 | PostgreSQL目录 + 规则评分 | 候选必须来自指标中心 |
| 指标消歧 | LLM + 置信门控 + 用户 | 只能在授权候选内选择 |
| DSL草稿 | LLM或确定性入口 | 输出受 Schema 约束的语义结构 |
| DSL校验 | 后端服务 | 校验指标、维度、时间和操作合法性 |
| SQL生成 | 确定性 Compiler | LLM 不拥有 SQL 执行权 |
| 数据执行 | ClickHouse只读服务 | 使用令牌、参数和查询快照 |
| 数据画像 | 确定性服务 | 计算趋势、贡献、质量和 Evidence |
| 业务解读 | Evidence兜底 / LLM | 数值必须绑定 Evidence |
| 可信校验 | Reflection Validator | 检查数字、单位、时间、因果和敏感信息 |

## 3. Workflow

主链包括上下文加载、预处理、指标检索、置信门控、澄清、DSL生成、DSL校验、SQL编译、安全门控、执行、画像、解读、Reflection、修订和 Data-only 降级。

Dify 是内部编排层，不是最终用户入口，也不是数据权限边界。前端通过产品 BFF 使用可信后端能力。

## 4. Prompt 管理现状

Prompt 当前保存在 Dify Workflow DSL，覆盖预处理、消歧、DSL生成和修订。主要约束包括：

- 只使用后端返回的指标及版本。
- 遵循确定的时间窗口和可用维度。
- 输出结构化 Schema。
- 解释只能引用提供的 Evidence。
- 不将描述性关系表述为确定性因果。

当前缺少 Prompt Registry、版本发布、灰度、回滚和在线实验。V1.3 应将 Prompt版本与每次评测运行关联。

## 5. RAG

当前没有向量 RAG。指标召回使用数据库目录和词项规则评分，数据本身也不会被批量放入 Prompt。

未来 RAG 的合理用途是检索指标说明、数据字典、业务术语、历史问法和治理文档；最终指标选择仍必须经过发布状态、权限和规则校验，向量相似度不能直接成为执行授权。

## 6. Tool 与 MCP

当前通过 HTTP 调用上下文、指标检索、DSL校验、Compiler、数仓、Profiler、Interpretation和Reflection服务，可称为工作流工具调用。

当前没有 MCP，也不应对外表述为使用了 MCP 或模型原生 Function Calling。MCP 只有在需要标准化接入更多分析工具且权限、审计收益明确时再评估。

## 7. Memory

当前为会话级结构化 Memory，按 `workspace_id + conversation_id` 保存上一轮指标、维度、筛选和时间范围。

继承时必须让用户可见，并允许新问题显式覆盖。权限、指标版本或数据源变化时不能盲目复用旧上下文。当前没有跨会话长期记忆、用户偏好记忆或向量记忆。

## 8. 可信机制

- 指标中心是口径唯一可信源。
- Query DSL 是 AI 与执行系统之间的契约。
- SQL由服务端白名单 Compiler生成。
- 每次查询记录指标版本、DSL Hash、SQL Fingerprint和血缘。
- 每条数值发现绑定 Evidence ID。
- Reflection检查未知证据、数字、单位、时间、版本、敏感信息和因果表述。
- 无法确认时采用澄清、拒绝或降级。

## 9. 模型与供应商策略

MVP 使用 Dify 中的 DeepSeek Chat，温度为0。模型不是产品核心锁定项；模型替换必须通过同一黄金问题集评测，并比较准确率、稳定性、耗时和成本。

## 10. 对外表述

推荐：`DataPath 通过 Agentic Workflow 编排语言理解、指标检索、DSL生成和多项可信工具。`

避免：`DataPath 是多 Agent 自主分析平台`、`使用了向量 RAG`、`已接入 MCP`、`AI 自动完成业务归因`。
