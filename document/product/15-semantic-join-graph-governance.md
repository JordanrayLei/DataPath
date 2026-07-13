# Semantic Join Graph 治理与发布工作台

> 版本：V2.0
> 更新日期：2026-07-13

## 1. 产品目标

Semantic Join Graph 将表关系从 SQL 隐式知识升级为可验证、可版本化、可审核的语义资产。Planner 只能使用已发布关系，避免模型自由猜 Join。

## 2. 当前数据模型

- `SemanticModel`：业务域、物理表、默认时间字段和状态。
- `SemanticEntity`：模型粒度、主键、实体类型和状态。
- `SemanticJoinRelation`：左右实体、键、基数、Join Type、Fanout 策略、优先级、版本和状态。
- `SemanticJoinDraft`：未发布的关系定义与验证结果。

## 3. 生命周期

```text
候选扫描
-> DRAFT
-> 数据验证
-> VALIDATED
-> PUBLISHED
-> DEPRECATED
```

当前前端和 API 已支持关系草稿保存、检测、发布和废弃。发布关系进入 Deterministic Planner，草稿和暂存关系不能参与在线 SQL 编译。

## 4. 自动检测

验证维度包括：

- 左右键非空覆盖率。
- 去重键数量与重复度。
- 推断基数。
- Join 覆盖率。
- Fanout 倍数和风险等级。
- 声明基数与实际数据是否一致。

自动扫描只生成候选，不自动发布。字段同名不是关系成立的充分证据。

## 5. 发布门禁

- 两端模型和实体必须存在且可用。
- Join 键必须属于允许字段。
- 键数量必须一致。
- 声明基数与检测结果不能冲突。
- `many_to_many` 默认阻断。
- `aggregate_before_join` 关系在聚合规划未实现前保持 `STAGED`。
- 发布必须记录版本与验证快照。

## 6. 当前 Olist Graph

已发布 5 条 `many_to_one + safe` 关系：订单商品到订单、商品、卖家，订单到客户，商品到品类翻译。

支付到订单、评价到订单为暂存的 `aggregate_before_join` 关系；地理位置因 Zip Prefix 多行和潜在 Fanout 未进入在线 Graph。

## 7. 管理 API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/chatbi/join-graph` | 获取模型、关系和草稿快照 |
| PATCH | `/api/chatbi/join-graph/models/{model_id}` | 更新模型治理字段 |
| PUT | `/api/chatbi/join-graph/drafts/{relation_id}` | 保存关系草稿 |
| POST | `/api/chatbi/join-graph/drafts/{relation_id}/validate` | 运行数据检测 |
| POST | `/api/chatbi/join-graph/drafts/{relation_id}/publish` | 发布验证通过的关系 |
| POST | `/api/chatbi/join-graph/relations/{relation_id}/deprecate` | 废弃关系 |
| POST | `/api/chatbi/join-graph/scan` | 扫描关系候选 |

## 8. 当前前端边界

当前工作台以列表和编辑表单为主，已发布与未发布关系的视觉区分不够直观。下一版应提供：

- 按状态分层或泳道展示。
- 节点/边 Graph 视图及图例。
- 影响模型、指标和黄金问题数量。
- 发布前后版本 Diff。
- 风险、覆盖率和 Fanout 的可视化编码。

## 9. 元数据同步计划

尚未实现定时元数据同步。规划流程：

```text
定时扫描数据库
-> 对比 Schema 快照
-> 识别表和字段变化
-> 标记受影响模型与关系
-> 生成变更候选
-> 通知负责人审核
```

在该能力完成前，新表、字段、模型和 Join Relation 仍需要人工触发扫描并审核维护。
