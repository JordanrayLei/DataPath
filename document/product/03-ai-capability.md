# DataPath AI 能力与可信架构

> 版本：V2.0
> 更新日期：2026-07-13

## 1. 能力定位

DataPath 是可信 ChatBI Copilot，采用 Agentic Workflow 组织语言理解、检索、规划、工具调用和可信校验。它不是多 Agent 自治系统，也不允许模型自由生成并执行 SQL。

## 2. 当前在线链路

浏览器调用 FastAPI `/api/chatbi/ask`。BFF 当前以代码方式编排完整链路，可在不依赖 Dify 的情况下完成问数：

```text
Context
-> Query Understanding
-> Metric Retrieval
-> Confidence Gate
-> Query DSL
-> Validator
-> Join Planner
-> SQL Compiler
-> ClickHouse Tool
-> Profiler / Evidence
-> Interpretation
-> Reflection
```

Dify DSL 是可选内部工作流资产，用于展示 LLM 预处理、候选消歧、DSL 草稿、修订和分支编排。它不是最终用户入口、权限边界或 SQL 安全边界。

## 3. AI 与确定性服务分工

| 能力 | 当前承担者 | 约束 |
| --- | --- | --- |
| Query Understanding | 默认规则 Provider；可切换结构化 HTTP/LLM Provider | 只输出受约束结构 |
| 指标召回 | 名称/别名、BM25、Embedding | 只召回已发布指标 |
| 候选排序 | 最长显式命中 + `qwen3-rerank` | Reranker 不覆盖发布与权限门禁 |
| 歧义处理 | 置信门禁与用户澄清 | 不确定时不执行 |
| DSL | 当前 BFF 确定性生成；Dify 可生成草稿 | 后端 Schema 与业务规则复核 |
| Join 规划 | Deterministic Planner | 只使用已发布安全关系 |
| SQL | 服务端 Compiler | 字段白名单、参数化、只读 |
| 数据执行 | ClickHouse Tool | 签名 Token、查询快照、Limit |
| 结果画像 | 确定性 Profiler | 生成趋势、贡献和 Evidence |
| 解读 | 确定性 fallback；Dify 可选 LLM | 数字必须来自 Evidence |
| 可信校验 | Reflection Validator | PASS / REVISE / BLOCK |

## 4. RAG 与语义检索

当前已实现面向指标语义资产的窄域 RAG，不对业务事实数据做向量化问答。

- Embedding：阿里云百炼 `text-embedding-v3`，1024 维。
- 向量库：PostgreSQL + pgvector + HNSW cosine。
- 文本检索：名称、别名、定义、正例和 BM25。
- Reranker：`qwen3-rerank`，仅在弱文本召回时参与相对排序。
- 当前索引：12 个指标、121 条语义文档、9 条能力边界样本。

向量相似度不是正确概率。最终选择还要结合完整名称优先、候选间距、边界反例、发布状态和授权状态。

## 5. Prompt

Dify DSL 中保留预处理、消歧、DSL、修订等 Prompt。当前在线 BFF 默认不依赖这些 Prompt，因此文档不得把某个 LLM 供应商描述为在线主链的必需组件。

尚未实现 Prompt Registry、版本发布、灰度、回滚和 Prompt 与评测运行的自动关联。

## 6. Agent 与 Tool Calling

当前工具边界包括上下文、检索、DSL 校验、SQL 编译、查询执行、结果画像和 Reflection 等后端 API。工具输入输出均使用 Pydantic/OpenAPI 契约，并通过服务令牌保护内部接口。

当前没有模型原生 Function Calling，也没有 MCP Server。对外可表述为“受控工具调用的 Agentic Workflow”，不能表述为“多 Agent 自治平台”。

## 7. Memory

`ConversationContext` 按 `workspace_id + conversation_id` 保存最近一次成功查询的指标、维度、筛选、时间范围和意图。

- 同一会话中可继承省略条件。
- 用户新提及的指标、维度或时间会覆盖旧条件。
- 新会话不继承历史上下文。
- 当前没有长期偏好记忆、跨会话画像或向量记忆。

## 8. 可信与降级

- 完整指标名和最长别名优先，减少短名称覆盖长名称。
- 多候选差距不足时返回 `CLARIFY`。
- 能力边界或未知指标返回 `REJECT`，危险动作应返回 `BLOCKED`。
- Embedding/Reranker 异常时回退到词法检索。
- LLM 不可用时使用确定性 Evidence 解读。
- 查询和解读均保存版本、Hash、血缘和 Evidence 引用。

## 9. 已知风险

- 当前状态门禁仍有 7 条标签不一致 Bad Case。
- 阈值基于本地 Olist 黄金集校准，不能直接迁移为其他业务域的固定常量。
- Reranker 与 Embedding 为外部服务，需补成本、限流、缓存和可观测性。
- Dify Workflow 是交付资产，但当前在线 BFF 与 Dify 存在两套编排实现，需要长期收敛或明确职责。
