# DataPath 产品文档

这组公开材料用于快速理解 DataPath 的产品定位、整体链路、核心取舍和实际产品页面。

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
| [AI 工作流设计](02-ai-workflow-design.md) | Dify 中的节点编排、AI 与确定性系统分工、输入输出和失败关闭分支 |
| [竞品研究与产品决策](06-competitive-research-and-product-decisions.md) | FineChatBI、Quick BI、Power BI、Looker 和 ThoughtSpot 的产品机制，以及这些观察如何影响 DataPath 的范围与取舍 |
| [产品页面截图](07-product-page-gallery.md) | 集中展示语义治理、可信问数与质量闭环的 10 个主要产品页面 |

## 阅读顺序

第一次了解项目，先阅读[产品概览](01-datapath-product-overview.md)，再通过[AI 工作流设计](02-ai-workflow-design.md)理解问数链路在 Dify 中如何落地，然后查看[产品页面截图](07-product-page-gallery.md)。最后阅读[竞品研究与产品决策](06-competitive-research-and-product-decisions.md)，了解项目为什么将重点放在受约束问数、AI 语义预热和持续质量闭环。
