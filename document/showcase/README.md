# DataPath 项目作品集

这里集中展示 DataPath 的产品方案、核心能力、关键设计与测评结果。

如果第一次了解项目，建议先看完整介绍 PPT，再根据关注点进入 PRD、测评方法或产品决策。

## 快速了解

### 项目全貌

[下载完整产品介绍（PPT）](完整产品介绍.pptx) · [查看 PDF](完整产品介绍.pdf)

PPT 通过真实运行界面、DDL 验收证据和产品交互稿，完整介绍：

- 数据接入与业务域治理；
- 指标中心、AI 语义预热和 Join Graph；
- 问数工作台、DSL、Evidence 与权限门禁；
- Schema 影响传播；
- Bad Case、Golden 回归和测评监控；
- 产品特点、项目资产与当前结果。

### 产品方案

在 PPT 之后阅读[产品总体 PRD](09-product-prd.md)。

总体 PRD 定义产品范围、完整功能规则、异常状态和版本验收。

### 专题设计

依次阅读：

1. [可信 ChatBI 竞品研究与产品决策](05-competitive-analysis.md)；
2. [产品流程图](06-product-flows.md)；
3. [事件埋点方案](07-event-tracking-plan.md)；
4. [权限设计](08-permission-design.md)；
5. [AI 语义预热 PRD](10-ai-semantic-preheat-prd.md)；
6. [Schema 影响管理 PRD](11-schema-impact-management-prd.md)；
7. [Bad Case—Golden 契约闭环 PRD](12-badcase-golden-contract-prd.md)；
8. [指标体系与测评方法](03-metrics-and-evaluation.md)；
9. [核心产品决策记录](04-product-decisions.md)。

这些文档分别展开竞争判断、质量闭环、测评体系和关键产品取舍。

## 推荐阅读顺序

| 顺序 | 材料 | 重点内容 | 适合了解 |
| ---: | --- | --- | --- |
| 1 | [完整产品介绍（PPT）](完整产品介绍.pptx) · [PDF](完整产品介绍.pdf) | 完整功能、真实界面、产品特点和结果 | 项目全貌 |
| 2 | [产品总体 PRD](09-product-prd.md) | 产品范围、完整功能、业务规则、异常状态和版本验收 | 需求定义 |
| 3 | [可信 ChatBI 竞品研究与产品决策](05-competitive-analysis.md) | 行业基线、竞品机制、产品边界、取舍依据与优先级 | 竞争判断 |
| 4 | [产品流程图](06-product-flows.md) | 产品全链路和四类角色操作流程 | 流程设计 |
| 5 | [事件埋点方案](07-event-tracking-plan.md) | 事件字典、产品漏斗、指标口径和数据质量 | 数据验证 |
| 6 | [权限设计](08-permission-design.md) | 角色、资源、数据范围、权限门禁与建设优先级 | 权限治理 |
| 7 | [AI 语义预热 PRD](10-ai-semantic-preheat-prd.md) | 冷启动问题、草稿生成、人机审核、AI 边界和专项评测 | 创新设计 |
| 8 | [Schema 影响管理 PRD](11-schema-impact-management-prd.md) | Schema Diff、影响传播、失败关闭和恢复门禁 | 创新设计 |
| 9 | [Bad Case—Golden 契约闭环 PRD](12-badcase-golden-contract-prd.md) | 现场冻结、归因、Golden、受影响回归和发布门禁 | 创新设计 |
| 10 | [指标体系与测评方法](03-metrics-and-evaluation.md) | 北极星指标、质量指标、评测集、Golden 和结果判定 | 测评体系 |
| 11 | [核心产品决策记录](04-product-decisions.md) | Text-to-SQL、人工治理、失败关闭、Join 与版本策略 | 产品取舍 |

## 按产品主题查看

| 产品主题 | 相关内容 |
| --- | --- |
| 产品定位与整体方案 | 完整介绍 PPT、产品总体 PRD |
| 竞争环境与差异化 | 可信 ChatBI 竞品研究与产品决策 |
| 产品链路与角色操作 | 产品流程图 |
| 产品使用与价值验证 | 事件埋点方案、指标体系与测评方法 |
| 角色、功能与数据访问边界 | 权限设计 |
| 指标治理与 AI 语义预热 | 完整介绍 PPT、AI 语义预热 PRD |
| 可信问数与结果证据 | 完整介绍 PPT、指标体系与测评方法 |
| Bad Case 数据闭环 | Bad Case—Golden 契约闭环 PRD、指标体系与测评方法 |
| Schema 变化影响管理 | 完整介绍 PPT、Schema 影响管理 PRD |
| 核心技术路线与产品取舍 | 核心产品决策记录 |

## 文件说明

### 主要展示材料

| 文件 | 说明 |
| --- | --- |
| [`完整产品介绍.pptx`](完整产品介绍.pptx) | 当前推荐使用的完整产品介绍 PPT |
| [`完整产品介绍.pdf`](完整产品介绍.pdf) | 无需 PowerPoint 即可查看的 PDF 版本 |
| [`09-product-prd.md`](09-product-prd.md) | DataPath 的产品范围、模块规则、异常状态和版本验收 |
| [`05-competitive-analysis.md`](05-competitive-analysis.md) | 可信 ChatBI 竞品研究、产品边界、决策评分和差异化策略 |
| [`06-product-flows.md`](06-product-flows.md) | 业务流程和用户操作流程 |
| [`07-event-tracking-plan.md`](07-event-tracking-plan.md) | 事件字典、漏斗、指标口径和数据质量 |
| [`08-permission-design.md`](08-permission-design.md) | 角色、资源、数据范围、权限规则和验收用例 |
| [`10-ai-semantic-preheat-prd.md`](10-ai-semantic-preheat-prd.md) | AI 语义预热创新模块详细 PRD |
| [`11-schema-impact-management-prd.md`](11-schema-impact-management-prd.md) | Schema 影响管理创新模块详细 PRD |
| [`12-badcase-golden-contract-prd.md`](12-badcase-golden-contract-prd.md) | Bad Case—Golden 契约闭环创新模块详细 PRD |
| [`03-metrics-and-evaluation.md`](03-metrics-and-evaluation.md) | 产品指标和 AI 测评方法 |
| [`04-product-decisions.md`](04-product-decisions.md) | 项目过程中的核心决策与代价 |

### 补充材料

| 文件 | 说明 |
| --- | --- |
| [`DataPath-项目功能介绍.pptx`](DataPath-项目功能介绍.pptx) | 以功能模块为主的补充讲解版本 |
| [`assets/product-evidence/`](assets/product-evidence/README.md) | README 和 PPT 使用的产品界面及运行证据 |

## 返回项目首页

[返回 DataPath README](../../README.md)
