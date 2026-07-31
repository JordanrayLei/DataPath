# 竞品研究与产品决策

DataPath 在产品设计初期需要回答一个问题：当市场上已经存在 FineChatBI、Quick BI、Power BI Copilot、Looker 和 ThoughtSpot，新的企业问数产品还能解决什么问题？

本次研究没有按数据源数量、图表数量和报表能力逐项比较，而是沿一次问数的生命周期观察：用户提问前，系统如何准备业务语义；用户提问时，系统如何理解并执行；答案出现问题后，产品如何继续改善。

资料更新至 2026 年 7 月 31 日，主要来自各产品官网和官方帮助文档。公开资料无法覆盖厂商的全部内部机制，本文的作用是说明 DataPath 的产品选择，而不是判断某项能力只属于哪一家产品。

---

## 1. 问数产品正在形成一套共同结构

从这些产品的公开方案看，企业问数正在收敛到两个核心部分：

```text
语义治理
    ↓
自然语言问数链路
```

语义治理先把数据库中的表、字段和计算逻辑组织成业务能够理解的指标、维度和关系；问数链路再负责理解用户问题、选择语义资产、生成查询并返回结果。

这套结构代替了早期更直接的 Text-to-SQL 思路。大模型不再仅凭表结构自由生成 SQL，而是在企业已经确认的业务语义和权限范围内工作。

### 1.1 语义治理：先定义系统可以回答什么

不同产品使用的名称不同，但解决的是同一类问题：

- FineChatBI 使用分析主题、指标维度、同义词和问答配置；
- Quick BI 使用数据集、分析主题和企业知识；
- Power BI Copilot 建立在 Semantic Model 上；
- Looker 使用 LookML 定义指标、维度和模型关系；
- ThoughtSpot 使用 governed semantic layer。

语义治理为 AI 提供了四类基础信息：

| 内容 | 解决的问题 |
| --- | --- |
| 指标与业务定义 | “收入”“订单量”等概念应该怎样计算 |
| 维度与关系 | 数据可以按什么方式分析，表之间如何连接 |
| 同义词与业务说明 | 用户语言如何映射到企业数据概念 |
| 权限与可用范围 | 当前用户可以访问哪些数据和指标 |

Power BI 进一步提供 AI data schema、AI instructions 和 Verified Answers，用于让 Semantic Model 更适合 Copilot 使用；Looker Data Agents 允许分析人员补充业务术语、优先字段和计算指令；ThoughtSpot Spotter Semantics 将业务定义、Join 逻辑、层级和安全规则统一提供给分析 Agent。

这说明语义治理已经从传统 BI 的建模能力，变成了企业 AI 问数的必要底座。

参考：[Power BI Prep data for AI](https://learn.microsoft.com/en-nz/power-bi/create-reports/copilot-prepare-data-ai)、[Looker Conversational Analytics](https://docs.cloud.google.com/looker/docs/conversational-analytics-overview)、[ThoughtSpot Spotter Semantics](https://www.thoughtspot.com/product/spotter-semantics)。

### 1.2 问数链路：再把业务问题变成数据答案

语义资产准备完成后，产品还需要一条稳定的问数链路。主流产品通常包含以下环节：

```text
用户提出问题
→ 识别业务意图和上下文
→ 匹配指标、维度与筛选条件
→ 生成并执行查询
→ 返回数据、图表和解释
→ 支持继续追问
```

FineChatBI 可以在字段存在歧义时让用户确认，并展示数据表、过滤条件和汇总方式；Quick BI 将问数继续延伸到数据解读、归因和报告；Looker 依据 LookML Explore 中的语义生成分析；ThoughtSpot 将自然语言转为用户可查看的 search tokens，再生成可追溯查询。

问数产品的竞争重点因此不再只是“能否生成 SQL”，而是：

- 是否选中了正确的业务指标；
- 是否继承企业已有的数据权限；
- 是否在正确的维度和关系上执行；
- 用户能否理解本轮使用的口径和条件；
- 系统如何处理无法确定或无法安全执行的问题。

参考：[FineChatBI 问数据](https://help.fanruan.com/finebi/doc-view-2580.html)、[Quick BI 智能小Q](https://help.aliyun.com/zh/quick-bi/user-guide/smartq)、[Looker Conversational Analytics](https://docs.cloud.google.com/looker/docs/conversational-analytics-overview)、[ThoughtSpot Spotter](https://www.thoughtspot.com/product/agents/spotter)。

### 1.3 五个产品的侧重点

| 产品 | 语义治理方式 | 问数链路特点 |
| --- | --- | --- |
| FineChatBI | 分析主题、指标维度、同义词和问答配置 | 复用 FineBI 模型、权限和可视化，强调数据管理员运营 |
| Quick BI | 数据集、分析主题和企业知识 | 从问数扩展到解读、归因、报告和 Agent |
| Power BI Copilot | Semantic Model、AI schema、AI instructions、Verified Answers | 在 Power BI 报表和 Copilot 体系内完成问答 |
| Looker | LookML、Explore 和 Data Agent instructions | 以 LookML 作为业务语义来源，提供受治理的对话分析 |
| ThoughtSpot Spotter | Governed semantic layer、AI Context、coaching | 使用可见 search tokens 和可追溯查询强化可信感知 |

几条产品路径各有优势，但共同方向非常清楚：**语义治理负责给 AI 划定业务边界，问数链路负责在边界内完成分析任务。**

---

## 2. 这套主流方案解决了什么

“语义治理 + 问数链路”解决了企业自然语言取数最核心的三个问题。

### 2.1 让业务语言落到统一口径

用户问的是“销售额”“下单数”“活跃客户”，数据库中存储的却是字段、表和计算表达式。语义层把这些业务概念与确定的计算方式关联起来，避免每次问数都由模型临时猜测口径。

### 2.2 把 AI 限制在企业允许的范围内

成熟产品会复用已有的数据模型和权限体系。用户只能访问自己有权查看的模型、指标和数据范围，AI 也不能因为自然语言表达不同而绕开原有权限。

### 2.3 让答案具备一定的解释基础

FineChatBI 展示解析思路，ThoughtSpot 展示 search tokens，Power BI 通过 Verified Answers 为关键问题提供人工确认的结果。它们都在尝试让用户知道系统使用了怎样的口径和条件，而不是只呈现一个无法核对的数字。

DataPath 需要具备同样的基础能力。因此，项目保留语义治理底座，并搭建了从候选召回、Query DSL、确定性校验到 Evidence 的完整问数链路。

---

## 3. 主流方案仍然留下了两个问题

语义治理和问数链路主要解决“系统回答这一刻”的问题，但问数质量还受到回答前和回答后的影响。

```text
回答前：指标已经建设，但系统是否理解用户会怎样提问？

回答时：系统能否基于语义和权限返回可信答案？

回答后：用户发现错误后，问题是否会约束下一次版本？
```

当前产品在中间环节投入最充分，而链路两端仍然存在继续设计的空间。

### 3.1 提问前：建好指标，不等于建好了语言覆盖

一项指标通常包含标准名称、业务定义、公式和可用维度，但真实用户很少完全照着标准名称提问。

例如，同一个“订单量”指标可能被用户表达为：

- 下单数；
- 订单有多少；
- 一共出了几单；
- 今年每个月的单量；
- 各区域订单情况。

它还可能与“支付订单量”“成交订单量”“退款订单量”等相邻指标混淆。

主流产品已经意识到这类问题：FineChatBI 提供同义词和推荐问题；Power BI 提供 AI instructions 与 Verified Answers；ThoughtSpot 提供 AI Context 和 coaching。

但这些机制仍然需要大量人工准备，或者要等系统积累了一定查询历史后才能发现缺口。对于一个刚上线的指标或业务域，第一批用户仍可能承担语言覆盖不足带来的召回失败和指标误选。

DataPath 要处理的第一个问题由此明确：**能否在用户真正提问前，主动完成一轮受控的语言准备？**

### 3.2 回答后：记录反馈，不等于控制问题复发

点赞、点踩、问数记录、coaching 和 Verified Answers 已经出现在多个产品中。这些能力可以收集用户评价，或为一部分关键问题提供人工确认的答案。

这些机制证明了反馈和人工验证的重要性，但一次用户反馈要真正进入质量闭环，还需要补齐几个环节：

- 保留用户反馈发生时的指标版本、查询条件、SQL 和结果；
- 判断问题发生在召回、指标裁决、上下文、权限、查询还是解释环节；
- 由人工确认正确指标、正确查询以及系统本应进入的状态；
- 修复后重放当前问题，同时检查是否影响其他问题；
- 回归失败时阻止对应版本发布。

如果反馈只停留在记录、工单或调优建议中，团队可以修复这一次问题，却难以证明后续模型、Prompt、语义资产或规则变化不会让它再次出现。

第二个问题发生在用户反馈之后：**能否把真实问题沉淀为可重复执行的质量契约，并让它参与发布决策？**

DataPath 的选择，是把这些分散的反馈和人工验证继续向后连接：从原运行现场到人工 Golden，再从 Golden 到受影响回归和发布门禁。重点不是增加一个反馈入口，而是让已经确认的问题持续约束后续版本。

参考：[Power BI Verified Answers](https://learn.microsoft.com/zh-cn/power-bi/create-reports/copilot-prepare-data-ai-verified-answers)、[ThoughtSpot Enterprise-grade AI and trust](https://www.thoughtspot.com/trust/enterprise-grade-ai)、[Quick BI 智能小Q](https://help.aliyun.com/zh/quick-bi/user-guide/smartq)。

---

## 4. DataPath 的产品选择

竞品研究最终没有导向一个更大的 BI 平台，而是把 DataPath 收敛为“一套基础链路 + 两个补充环节”。

```text
AI 语义预热
    ↓
语义治理底座 + 受约束的可信 AI 问数
    ↓
持续质量闭环
```

语义治理和可信问数保证产品基本成立；两个创新点分别解决主流问数链路前后的质量问题。

### 4.1 基础实现：语义治理底座

DataPath 使用业务域、语义模型、指标、维度、Join 关系、权限和资产状态，定义问数系统可以使用的业务事实。

底座需要满足几项基本要求：

- 只有已经发布且用户有权访问的指标可以进入召回；
- 指标具有明确的定义、公式、聚合方式和版本；
- 维度与 Join 关系经过治理；
- 资产状态发生变化后，可以影响问数许可；
- 查询结果能够追溯到对应的指标和语义版本。

这些内容是问数产品的基础，与成熟指标平台的建设方向一致，因此在作品中只说明它如何约束 AI，不展开完整指标平台的审批、资产市场和组织治理流程。

### 4.2 主线实现：受约束的可信 AI 问数

DataPath 没有把自然语言直接交给大模型生成并执行 SQL，而是拆成一条可检查的链路：

```text
身份与会话上下文
→ 授权范围内召回有限候选
→ 指标裁决或要求澄清
→ 生成 Query DSL
→ 校验权限、维度、Join、资产、安全和成本
→ 确定性编译 SQL 并只读执行
→ 生成 Evidence
→ 基于 Evidence 解释结果
```

这条链路有四种正常产品结果：

| 状态 | 含义 |
| --- | --- |
| `SUCCESS` | 问题明确，查询与证据均通过 |
| `CLARIFY` | 存在合理歧义或缺少必要条件，需要用户确认 |
| `REJECT` | 问题超出当前业务域或治理范围 |
| `BLOCKED` | 权限、Join、资产、安全或成本门禁失败 |

可信问数本身不是相对头部产品的独有功能，而是 DataPath 承接两个创新点的主链路：预热资产最终进入候选召回，用户反馈最终引用本次 Query Run 和 Evidence。

### 4.3 创新点一：AI 语义预热

AI 语义预热把语言建设从用户提问后前移到指标上线前：

```text
读取已确认的指标事实
→ 检查现有语言资产的完整度
→ AI 生成别名、典型问法和相邻指标反例
→ 人工接受、编辑或拒绝
→ 检查别名冲突和不可变字段
→ 运行固定集评测
→ 发布新的语义版本与检索索引
```

AI 只负责扩展“用户可能怎样表达”，不会改变“指标应该怎样计算”。指标公式、聚合方式、模型、维度、Join 和权限保持不变，未经人工审核的内容也不会进入线上召回。

与常见的同义词和推荐问题配置相比，DataPath 重点补充了三个环节：

1. 在真实问数发生前主动诊断语言缺口；
2. 同时生成正向问法和反向边界，避免只提高召回而放大误召回；
3. 将人工审核后的语言资产继续接入冲突检查和固定集评测。

它要验证的不是 AI 能生成多少内容，而是新指标进入问数时，人工准备时间是否下降，正确指标召回是否提升，同时相邻指标误选是否保持在门槛内。

### 4.4 创新点二：持续质量闭环

持续质量闭环从一次真实用户反馈开始：

```text
用户提交反馈
→ 冻结原 Query Run、DSL、指标版本、结果和 Evidence
→ 人工确认有效 Bad Case
→ 定位错误发生的环节
→ 人工定义 Golden 契约
→ 修复对应的语义、规则或产品资产
→ 运行当前问题、相关 Golden 和安全用例
→ 通过后发布，失败则返回修复
```

DataPath 的 Golden 不只保存问题和正确 SQL，还需要表达：

- 预期产品状态；
- 预期指标；
- 关键 Query DSL 约束；
- 结果 Oracle 或结果不变量；
- 来源反馈、审核人和适用版本。

这样，一条反馈才从“用户认为结果不对”变成“系统今后必须持续满足的行为”。修复完成也不再以工单关闭为准，而是由目标用例、相关回归和安全门禁共同判断。

---

## 5. 为什么选择这两个创新点

### 5.1 它们位于主流方案最薄弱的两端

语义治理和问数链路已经被头部产品反复验证，DataPath 没有必要重新定义它们。语义预热位于用户提问前，持续质量闭环位于用户反馈后，两者分别补足语言冷启动和问题复发。

### 5.2 它们可以与现有主链路形成数据关系

两个模块不是独立工具：

```text
预热产生的语言资产
→ 进入可信问数的候选召回
→ 问数产生 Query Run 和 Evidence
→ 用户反馈引用本次运行
→ Golden 约束修复和发布
→ 已确认的新表达再回流语言资产
```

产品价值来自这条数据闭环，而不是两个额外页面。

### 5.3 它们适合用产品指标验证

| 模块 | 需要验证的结果 |
| --- | --- |
| AI 语义预热 | 单指标准备时长、建议采纳率、Recall@3、相邻指标误召回率 |
| 可信 AI 问数 | 正确终态率、错误指标选择数、澄清完成率、未授权执行数、Evidence 完整率 |
| 持续质量闭环 | 现场快照完整率、可归因率、Golden 完整率、受影响回归覆盖率、同类问题复发率 |

如果 AI 草稿的审核成本不低于人工直接配置，语义预热就没有产生效率价值；如果大量可回答问题被错误阻断，可信问数的语义覆盖和澄清机制仍需调整；如果建立 Golden 的成本过高，质量闭环则需要只覆盖高风险、高频或具有代表性的问题。

---

## 6. 产品边界

竞品研究也明确了 DataPath 当前不需要展开的方向。

| 方向 | 当前处理方式 |
| --- | --- |
| 完整指标管理平台 | 保留支撑问数所需的指标、维度、关系、权限和版本，不展开全部平台流程 |
| 报表、仪表板和大屏 | 提供结果展示所需的基础图表，不参与组件数量竞争 |
| 数据源连接器 | 先验证产品链路，不以连接数量作为当前重点 |
| 报告生成与办公协同 | 属于成熟 BI 的功能扩展，暂不进入主线 |
| 自由 Text-to-SQL | 不采用，AI 输出结构化意图，SQL 由服务端编译 |
| 追求所有问题都有答案 | 不采用，澄清、拒绝和阻断都是正常产品结果 |

DataPath 的范围因此保持在一个更具体的问题上：如何让已经治理的企业指标更容易被用户正确提问，让每次查询在明确边界内执行，并让真实错误持续约束后续版本。

---

## 7. 最终产品决策

本次研究得到的核心判断是：

> 企业问数产品正在形成“语义治理 + 问数链路”的共同结构。它解决了业务口径、权限和自然语言查询的基本问题，但提问前的语言冷启动与反馈后的复发控制仍值得继续设计。

DataPath 在这套主流结构上保留必要基础，并选择两个与主链路直接相连的创新点：

```text
一个底座：语义治理

一条主线：受约束的可信 AI 问数

两个创新：AI 语义预热 + 持续质量闭环
```

后续建设优先级也围绕这套结构展开：先保证可信问数链路的四种终态和 Evidence 完整，再验证语义预热是否改善冷启动，最后验证 Bad Case、Golden、回归和发布门禁是否真正降低问题复发。

这使 DataPath 不需要与成熟 BI 比较功能广度，也不依赖单次准确率建立产品价值。项目要证明的是：企业问数除了把问题转换成答案，还可以在提问前准备语言，在不确定时主动停下来，并在发生错误后让系统持续记住正确行为。

---

## 参考资料

### FineChatBI / FineBI

- [FineChatBI 产品介绍](https://help.fanruan.com/finebi-en/doc-view-6056.html)
- [FineChatBI 问数据](https://help.fanruan.com/finebi/doc-view-2580.html)
- [FineChatBI 大模型配置](https://help.fanruan.com/finebi/doc-view-2631.html)
- [FineChatBI 预加载配置](https://help.fanruan.com/finebi-en/doc-view-6054.html)
- [FineChatBI 使用权限配置](https://help.fanruan.com/finebi-en/doc-view-6051.html)

### Quick BI

- [Quick BI 产品概述](https://help.aliyun.com/zh/quick-bi/product-overview/introduction-to-quick-bi-1)
- [智能小Q概述](https://help.aliyun.com/zh/quick-bi/user-guide/smartq)
- [Quick BI v6.2 版本说明](https://help.aliyun.com/zh/quick-bi/product-overview/quick-bi-v6-2-release-notes)

### Power BI

- [Prepare your data for AI](https://learn.microsoft.com/en-nz/power-bi/create-reports/copilot-prepare-data-ai)
- [Power BI Verified Answers](https://learn.microsoft.com/zh-cn/power-bi/create-reports/copilot-prepare-data-ai-verified-answers)

### Looker

- [Conversational Analytics overview](https://docs.cloud.google.com/looker/docs/conversational-analytics-overview)
- [Conversational data agents](https://cloud.google.com/looker/docs/studio/conversational-data-agents-looker)

### ThoughtSpot

- [ThoughtSpot Spotter](https://www.thoughtspot.com/product/agents/spotter)
- [Enterprise-grade AI and trust](https://www.thoughtspot.com/trust/enterprise-grade-ai)
- [Spotter Semantics](https://www.thoughtspot.com/product/spotter-semantics)
