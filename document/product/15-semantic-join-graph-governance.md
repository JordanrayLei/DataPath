# Semantic Join Graph 治理与发布工作台

> 版本：V1.0  
> 状态：已实现  
> 日期：2026-07-12

## 产品目标

将 Join 关系从代码种子配置升级为可发现、可检测、可审核、可版本化的语义资产。自动化负责提供候选和数据证据，人工负责业务粒度和发布决策。

## 工作流

`DISCOVERED -> DRAFT -> VALIDATED -> PUBLISHED -> DEPRECATED`

- 扫描：读取 ClickHouse 表字段，将“左表包含右实体受治理主键”生成候选。
- 草稿：人工确认实体、Join Key、基数、Join类型和 Fanout 策略。
- 检测：计算左右表行数、右键唯一率、覆盖率和 Join 膨胀倍数。
- 发布：只有通过安全门禁的草稿生成不可变版本，并进入 Planner。
- 废弃：关系从 Planner 的 `PUBLISHED` 可用集中移除，历史版本保留。

## 发布门禁

- 左右 Key 数量必须一致。
- 两个实体必须属于同一业务域。
- 只有 `one_to_one` 和 `many_to_one` 可进入安全发布评估。
- 右键唯一率必须至少 99.9%。
- Fanout 倍数不得超过 1.001。
- 未通过时推荐 `aggregate_before_join`，不允许发布为 `safe`。

## API

- `GET /api/chatbi/join-graph`
- `PATCH /api/chatbi/join-graph/models/{model_id}`
- `PUT /api/chatbi/join-graph/drafts/{relation_id}`
- `POST /api/chatbi/join-graph/drafts/{relation_id}/validate`
- `POST /api/chatbi/join-graph/drafts/{relation_id}/publish`
- `POST /api/chatbi/join-graph/relations/{relation_id}/deprecate`
- `POST /api/chatbi/join-graph/scan`

## 当前边界

- 自动扫描是基于受治理主键和字段同名的确定性推荐，不是 LLM 自动发布。
- V1 不自动推断业务粒度，需由数据负责人确认。
- `aggregate_before_join` 可作为草稿策略保存，对应 SQL 子查询编译属于下一阶段。

## 未来优化：Graph可视化

当前列表式界面可完成治理操作，但对关系全景和发布状态的表达不够直观。未来可升级为“拓扑图 + 状态筛选 + 关系详情 + 发布队列”：

- 实线、虚线和明确文字标签区分 `PUBLISHED`、`VALIDATED`、`DRAFT`、高风险和 `DEPRECATED`。
- 提供“仅看 Planner 可用关系”开关，只展示 `ACTIVE + PUBLISHED + safe` 路径。
- 点击关系后展示基数、覆盖率、唯一率、Fanout、版本和发布操作。
- 独立展示自动候选、待检测、验证失败、等待发布和最近发布队列。
- 优先考虑 Cytoscape.js 接入现有原生 JavaScript 前端，不在当前版本实施。

## 未来优化：元数据定时同步

后续增加元数据同步任务，定时扫描数仓并与上一次 Schema 快照对比：

`定时扫描 -> Schema快照对比 -> 识别表和字段变化 -> 标记受影响模型与关系 -> 生成变更候选 -> 通知负责人审核`

该能力只生成变更证据、风险标记和待审核候选，不自动覆盖、废弃或发布 Semantic Model、Entity 和 Join Relation。
