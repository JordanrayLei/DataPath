# DataPath 产品文档

这组文档记录 DataPath 从产品定位、核心链路到两个重点模块的完整设计，并说明这些选择来自怎样的竞品观察。

DataPath 以语义治理为底座，围绕一条受约束的可信 AI 问数链路展开：提问前通过 AI 语义预热补充语言覆盖，回答时由确定性规则控制指标、权限、关系和执行边界，回答后将真实问题接入 Golden、回归和发布门禁。

```text
语义治理底座
    ↓
AI 语义预热
    ↓
受约束的可信 AI 问数
    ↓
持续质量闭环
```

## 文档目录

| 文档 | 内容 |
| --- | --- |
| [DataPath 产品概览](01-datapath-product-overview.md) | 产品定位、目标用户、整体结构、核心链路、当前实现和产品边界 |
| [受约束的可信 AI 问数 PRD](02-constrained-trusted-ai-query-prd.md) | 从用户提问到可信答案的完整链路，包括候选召回、澄清、Query DSL、确定性门禁、执行、Evidence 和错误兜底 |
| [AI 语义预热 PRD](03-ai-semantic-preheat-prd.md) | 指标进入问数前的语言准备流程，包括完整度诊断、AI 草稿、正反例、人工审核、冲突检查和版本发布 |
| [持续质量闭环 PRD](04-continuous-quality-loop-prd.md) | 用户反馈如何转化为 Bad Case、Golden 契约、受影响回归和发布门禁 |
| [竞品研究与产品决策](05-competitive-research-and-product-decisions.md) | FineChatBI、Quick BI、Power BI、Looker 和 ThoughtSpot 的产品机制，以及这些观察如何影响 DataPath 的范围与取舍 |

## 阅读顺序

第一次了解项目，可以先阅读[产品概览](01-datapath-product-overview.md)，再进入[受约束的可信 AI 问数 PRD](02-constrained-trusted-ai-query-prd.md)。这两份文档分别说明产品整体结构和主要使用链路。

两个创新模块位于主链路的前后：

- [AI 语义预热 PRD](03-ai-semantic-preheat-prd.md)处理用户提问前的语言冷启动；
- [持续质量闭环 PRD](04-continuous-quality-loop-prd.md)处理用户反馈后的修复与复发控制。

[竞品研究与产品决策](05-competitive-research-and-product-decisions.md)可以最后阅读，用来了解为什么项目没有继续扩展完整指标平台、报表和大屏，而是把精力集中在可信问数与质量闭环。
