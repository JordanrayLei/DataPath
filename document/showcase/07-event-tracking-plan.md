# DataPath 事件埋点方案

## 1. 埋点设计原则

### 1.1 事件描述已发生的事实

事件名使用“对象 + 已完成动作”，例如 `question_submitted`、`query_executed`。按钮曝光、页面停留等弱信号不用于推断业务结果。

### 1.2 前后端各自记录可信事实

- 前端记录用户显式操作，例如“结果可直接使用”；
- 后端记录处理结果，例如召回完成、查询执行、发布门禁；
- 关键成功状态以后端结果为准，不能仅依赖点击或页面展示。

### 1.3 全链路可以关联

问数链路通过 `trace_id`、`query_id` 和 `conversation_hash` 关联；治理链路通过 `workspace_id`、资产 ID、版本和反馈 ID 关联。

### 1.4 不采集不必要的敏感数据

默认不在产品事件表中保存：

- 原始自然语言问题；
- 编译 SQL；
- 查询结果行；
- 明文用户 ID；
- 明文会话 ID；
- 数据库连接信息或访问令牌。

### 1.5 不能用系统行为代替用户价值

查询执行成功不等于答案有用，页面展示不等于结果被采用。采用与人工修正必须来自用户显式操作。

## 2. 事件模型

### 2.1 公共字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_id` | string | 是 | 事件唯一 ID，格式为 `evt_*` |
| `workspace_id` | string | 是 | 工作空间 |
| `actor_hash` | string | 是 | 用户标识哈希，不保存明文 |
| `conversation_hash` | string | 是 | 会话标识哈希，不保存明文 |
| `trace_id` | string | 是 | 一次服务端处理链路的追踪 ID |
| `query_id` | string | 否 | 已进入编译或执行阶段时关联查询 |
| `event_name` | string | 是 | 事件名称 |
| `status` | string | 是 | 事件结果状态 |
| `reason_code` | string | 否 | 结构化原因码 |
| `properties_json` | object | 是 | 事件特有属性 |
| `duration_ms` | integer | 否 | 事件或处理阶段耗时 |
| `created_at` | datetime | 是 | 服务端写入时间，使用带时区时间 |

### 2.2 公共属性

| 属性 | 适用范围 | 说明 |
| --- | --- | --- |
| `traffic_class` | 问数链路 | `interactive` 或 `test`，避免测试流量污染产品分析 |
| `biz_domain` | 问数与治理 | 当前业务域 |
| `metric_id` | 指标相关事件 | 指标稳定 ID |
| `metric_version` | 指标相关事件 | 指标版本 |
| `role_id` | 权限分析 | 建议只保存角色，不保存个人身份 |
| `source` | 多入口事件 | 触发入口，例如 `workbench`、`metric_center` |

## 3. 已实现事件清单

### 3.1 在线问数事件

| 事件名 | 触发时机 | 记录端 | 关键属性 | 用途 |
| --- | --- | --- | --- | --- |
| `question_submitted` | 服务端收到有效问数请求 | 后端 | `question_hash`、`question_length`、`biz_domain`、`is_followup`、`traffic_class` | 提问规模、追问率和漏斗起点 |
| `retrieval_completed` | 指标召回与召回门禁完成 | 后端 | `candidate_count`、`top1_metric_id`、`top1_score`、`top1_margin`、`retrieval_sources` | 召回质量与歧义分析 |
| `metric_judge_completed` | 有限候选裁决被调用并返回 | 后端 | `provider`、`model`、`confidence`、`selected_metric_id`、`fallback` | 模型裁决效果与降级分析 |
| `status_decided` | 请求得到最终产品状态 | 后端 | `status`、`reason_code`、`pipeline_terminal_step`、`duration_ms` | SUCCESS、CLARIFY、REJECT、BLOCKED 分布 |
| `query_executed` | 只读查询执行完成 | 后端 | `metric_id`、`metric_version`、`row_count`、`execution_ms`、`estimated_rows` | 执行成功率、性能和资源量 |
| `answer_rendered` | 结果解读与 Reflection 完成 | 后端 | `status`、`evidence_count`、`chart_type` | 可信答案率与 Evidence 覆盖 |

### 3.2 用户价值事件

| 事件名 | 触发时机 | 记录端 | 关键属性 | 用途 |
| --- | --- | --- | --- | --- |
| `result_adopted` | 用户点击“结果可直接使用” | 前端请求、后端落库 | `query_id`、`reason_code=EXPLICIT_USER_ACTION` | 显式结果采用率 |
| `result_corrected` | 用户点击“结果经过人工修正” | 前端请求、后端落库 | `query_id`、`reason_code=EXPLICIT_USER_ACTION` | 人工修正率 |
| `feedback_submitted` | 用户成功提交 Bad Case | 后端 | `feedback_type`、`severity`、`query_id` | 问题反馈率与问题结构 |

`result_adopted` 和 `result_corrected` 按 `workspace_id + query_id + event_name` 去重，重复点击不重复计数。

### 3.3 治理事件

| 事件名 | 触发时机 | 记录端 | 关键属性 | 用途 |
| --- | --- | --- | --- | --- |
| `badcase_closure_validated` | Bad Case 契约执行关闭校验 | 后端 | `feedback_id`、校验结果、关联版本 | 关闭门禁通过率 |
| `metric_version_published` | 指标新版本发布成功 | 后端 | `metric_id`、`metric_version`、发布上下文 | 发布数量及与修复链路关联 |

## 4. 规划补充事件

### 4.1 AI 语义预热

| 事件名 | 优先级 | 触发时机 | 建议属性 |
| --- | --- | --- | --- |
| `metric_draft_saved` | P0 | 指标草稿通过基础校验并保存 | `metric_id`、`completeness_score`、`missing_item_count` |
| `preheat_generation_started` | P1 | 用户确认发起生成 | `metric_id`、`metric_version`、`input_asset_count` |
| `preheat_generation_completed` | P0 | 预热草稿生成结束 | `status`、`duration_ms`、`alias_count`、`positive_count`、`negative_count` |
| `preheat_draft_edited` | P1 | 人工修改生成内容并保存 | `edited_field_types`、`edited_item_count` |
| `preheat_applied` | P0 | 人工确认并应用草稿 | `accepted_item_count`、`rejected_item_count`、`modified_item_count` |
| `preheat_reverted` | P1 | 已应用语义资产被撤回 | `reason_code`、`affected_item_count` |

### 4.2 Bad Case 与 Golden

| 事件名 | 优先级 | 触发时机 | 建议属性 |
| --- | --- | --- | --- |
| `badcase_triaged` | P0 | 运营人员确认反馈有效性和类别 | `feedback_id`、`valid`、`category`、`severity` |
| `badcase_root_cause_confirmed` | P0 | 根因层级被确认 | `feedback_id`、`root_cause_layer`、`owner_role` |
| `golden_contract_created` | P0 | 正确终态与 Oracle 保存为 Golden | `feedback_id`、`golden_id`、`expected_status`、`metric_id` |
| `regression_run_started` | P1 | 发起当前和受影响回归 | `run_id`、`trigger_type`、`case_count` |
| `regression_run_completed` | P0 | 回归完成 | `run_id`、`status`、`passed`、`failed`、`gate_failures` |
| `badcase_resolved` | P0 | 修复版本发布且问题关闭 | `feedback_id`、`resolution_type`、`lead_time_hours` |
| `badcase_reopened` | P1 | 已关闭问题因复现被重新打开 | `feedback_id`、`reason_code` |

### 4.3 Schema 影响管理

| 事件名 | 优先级 | 触发时机 | 建议属性 |
| --- | --- | --- | --- |
| `schema_scan_completed` | P0 | 数据源重新扫描完成 | `source_id`、`duration_ms`、`table_count`、`column_count` |
| `schema_change_detected` | P0 | 快照对比发现变化 | `source_id`、`change_type`、`change_count`、`breaking` |
| `schema_impact_propagated` | P0 | 影响传播完成 | `domain_count`、`model_count`、`join_count`、`metric_count` |
| `governance_asset_degraded` | P0 | 资产因变化被降级 | `asset_type`、`asset_id`、`reason_code` |
| `schema_validation_completed` | P0 | 修复后重新验收完成 | `status`、`checked_asset_count`、`failed_asset_count` |
| `governance_asset_republished` | P0 | 负责人复核并重新发布 | `asset_type`、`asset_id`、`asset_version`、`recovery_hours` |

### 4.4 Evidence 使用

| 事件名 | 优先级 | 触发时机 | 建议属性 |
| --- | --- | --- | --- |
| `evidence_panel_opened` | P1 | 用户主动展开 Evidence | `query_id`、`evidence_count` |
| `result_detail_viewed` | P1 | 用户从图表切换到数据表 | `query_id`、`row_count` |
| `result_exported` | P1 | 导出成功 | `query_id`、`export_type`、`row_count` |

这些事件衡量“用户是否感知可信机制”，但不能代替结果采用事件。

## 5. 核心漏斗

### 5.1 可信问数漏斗

```text
question_submitted
→ status_decided=SUCCESS
→ query_executed
→ answer_rendered=PASS
→ result_adopted
```

| 指标 | 计算口径 |
| --- | --- |
| 请求接受率 | `status_decided(SUCCESS) / question_submitted` |
| 执行到达率 | `query_executed / question_submitted` |
| 可信答案率 | `answer_rendered(PASS) / question_submitted` |
| 成功结果采用率 | `result_adopted / answer_rendered(PASS)` |
| 人工修正率 | `result_corrected / answer_rendered(PASS)` |
| 反馈率 | `feedback_submitted / answer_rendered(PASS)` |

所有产品指标默认只统计 `traffic_class=interactive`，自动测试和发布回归流量单独展示。

### 5.2 澄清恢复漏斗

```text
status_decided=CLARIFY
→ 同一 conversation_hash 再次 question_submitted
→ status_decided=SUCCESS
→ answer_rendered=PASS
```

| 指标 | 计算口径 |
| --- | --- |
| 澄清率 | `CLARIFY 请求数 / question_submitted` |
| 澄清继续率 | `澄清后再次提问会话数 / CLARIFY 会话数` |
| 澄清恢复率 | `澄清后成功会话数 / CLARIFY 会话数` |
| 平均澄清轮数 | 成功前澄清次数的平均值 |
| 澄清放弃率 | 在观察窗口内无后续提问的 CLARIFY 会话数 / CLARIFY 会话数 |

建议观察窗口为 30 分钟，并在指标说明中固定，避免不同报表使用不同窗口。

### 5.3 AI 预热漏斗

```text
metric_draft_saved
→ preheat_generation_completed
→ preheat_applied
→ metric_version_published
```

| 指标 | 计算口径 |
| --- | --- |
| 预热使用率 | 发起预热的指标数 / 可预热指标数 |
| 生成成功率 | 成功生成次数 / 生成发起次数 |
| 草稿采纳率 | `accepted_item_count / generated_item_count` |
| 草稿修改率 | `modified_item_count / generated_item_count` |
| 预热后发布率 | 预热应用后发布指标数 / 预热应用指标数 |
| 上线准备时长 | 首次保存草稿到首次发布的中位时长 |

预热价值需要结合上线后的首轮召回率和误召回率判断，不能只看生成数量。

### 5.4 Bad Case 闭环漏斗

```text
feedback_submitted
→ badcase_triaged(valid=true)
→ golden_contract_created
→ regression_run_completed(PASS)
→ badcase_resolved
```

| 指标 | 计算口径 |
| --- | --- |
| 有效反馈率 | 有效 Bad Case / feedback_submitted |
| 契约转化率 | golden_contract_created / 有效 Bad Case |
| 首次回归通过率 | 首次回归通过问题数 / 发起回归问题数 |
| 问题关闭率 | badcase_resolved / 有效 Bad Case |
| 闭环周期 | feedback_submitted 到 badcase_resolved 的 P50、P95 |
| 复发率 | badcase_reopened / badcase_resolved |

### 5.5 Schema 恢复漏斗

```text
schema_change_detected(breaking=true)
→ schema_impact_propagated
→ governance_asset_degraded
→ schema_validation_completed(PASS)
→ governance_asset_republished
```

| 指标 | 计算口径 |
| --- | --- |
| 破坏性变化占比 | breaking 变化数 / 全部变化数 |
| 影响传播成功率 | 完成影响传播的破坏性变化 / 破坏性变化 |
| 错误放行数 | 受影响资产降级后仍成功执行的查询数 |
| 验收通过率 | PASS 验收 / 全部重新验收 |
| 资产恢复时长 | 资产降级到重新发布的 P50、P95 |

`错误放行数`属于安全门禁指标，目标必须为 0，不能被总体成功率抵消。

## 6. 北极星指标与指标树

### 6.1 建议北极星指标

**每周可信答案采用数**

定义：

> 每周由交互用户发起、经过完整可信门禁、Reflection 为 PASS，并被用户显式标记为可直接使用的去重查询数。

这个指标同时要求：

- 用户真实提出问题；
- 系统完成可信执行；
- 用户明确认可结果价值。

指标计算必须区分 `interactive` 与 `test` 流量，产品采用指标只使用符合既定统计口径的交互事件。

### 6.2 指标树

```text
每周可信答案采用数
├── 有效提问用户数
├── 人均提问数
├── 请求接受率
├── 可信答案率
└── 成功结果采用率
```

护栏指标：

- 危险执行数 = 0；
- 错误指标选择数 = 0；
- 越权执行数 = 0；
- Schema 受影响资产错误放行数 = 0；
- P95 端到端响应时间；
- 人工修正率；
- Bad Case 复发率。

## 7. 事件属性详细口径

### 7.1 `status` 口径

| 状态 | 定义 |
| --- | --- |
| `SUCCESS` | 可信门禁通过并进入成功结果链路 |
| `CLARIFY` | 需要用户补充口径或从候选中选择 |
| `REJECT` | 危险意图或超出产品支持范围 |
| `BLOCKED` | 权限、Schema、治理状态或可信门禁阻止执行 |
| `PASS` | 某一校验或 Reflection 通过 |
| `FAIL` | 某一校验、回归或发布门禁失败 |

### 7.2 `reason_code` 要求

- 必须使用稳定枚举，不保存自由文本；
- 一个事件只记录主原因，详细原因放在结构化属性；
- 历史枚举不可改变含义，只能新增；
- 报表展示枚举对应的中文说明；
- 未知原因使用 `UNKNOWN`，不能留空掩盖数据问题。

建议分组：

| 分组 | 示例 |
| --- | --- |
| 召回 | `NO_CANDIDATE`、`AMBIGUOUS_METRIC`、`LOW_CONFIDENCE` |
| 权限 | `ROLE_DENIED`、`DOMAIN_DENIED`、`ROW_SCOPE_DENIED` |
| Schema | `MODEL_IMPACTED`、`JOIN_IMPACTED`、`METRIC_STALE` |
| 安全 | `DDL_INTENT`、`DML_INTENT`、`FREE_SQL_REJECTED` |
| 质量 | `REFLECTION_FAILED`、`ORACLE_MISMATCH`、`GOLDEN_FAILED` |

### 7.3 时长口径

| 指标 | 起点 | 终点 |
| --- | --- | --- |
| 端到端响应时间 | 服务端接受问数请求 | 最终状态决定 |
| 查询执行时间 | 发起 ClickHouse 请求 | 收到完整结果 |
| 预热生成时间 | 生成任务受理 | 草稿成功或失败 |
| Bad Case 闭环时间 | 反馈成功创建 | 问题成功关闭 |
| Schema 恢复时间 | 资产被标记降级 | 新版本重新发布 |

## 8. 数据质量与验收

### 8.1 上线验收

每个新事件必须验证：

- 正常路径只记录一次；
- 重复点击符合去重策略；
- 失败路径记录正确状态和原因；
- `workspace_id`、`trace_id` 等关联字段完整；
- 测试流量能被标记并排除；
- 不包含原始问题、SQL、结果行和令牌；
- 属性类型与数据字典一致；
- 事件时间使用服务端时间。

### 8.2 每日数据质量检查

| 检查项 | 告警条件 |
| --- | --- |
| 事件量突降 | 较近 7 日同周期均值下降 50% 以上 |
| 孤立执行事件 | `query_executed` 找不到对应 `question_submitted` |
| 成功无答案事件 | `status_decided=SUCCESS` 但无 `answer_rendered` |
| 答案无 Evidence | `answer_rendered=PASS` 且 `evidence_count=0` |
| 未分类阻断 | `BLOCKED` 或 `REJECT` 的 `reason_code` 为空 |
| 测试流量污染 | 自动评测会话被标记为 `interactive` |
| 隐私字段泄漏 | 属性出现 question、sql、token 或 result_rows 明文 |

### 8.3 版本管理

- 事件定义变更必须更新本文档；
- 属性删除至少提前一个版本标记废弃；
- 指标计算需要记录版本号；
- 报表口径变更不得回写历史含义；
- 事件新增后先在测试环境验证，再进入正式统计。

## 9. 看板设计

### 9.1 产品总览

- 交互提问数；
- SUCCESS、CLARIFY、REJECT、BLOCKED 分布；
- 可信答案率；
- 显式采用率和人工修正率；
- 端到端响应时间 P50、P95；
- 四项安全门禁。

### 9.2 召回与模型

- 候选数量分布；
- Top1 分数和 Margin 分布；
- 各召回源使用率；
- 模型裁决调用率、接受率和 fallback 率；
- 按指标统计澄清率、反馈率和修正率。

### 9.3 质量闭环

- 新增、处理中、已解决 Bad Case；
- 根因层级分布；
- 契约转化率；
- 回归通过率；
- 闭环周期；
- 复发率。

### 9.4 治理健康

- 指标草稿与发布数量；
- AI 预热生成、应用和修改率；
- Schema 变化和受影响资产；
- 降级资产数量与恢复时间；
- 发布门禁失败原因。

## 10. 实施优先级

| 阶段 | 目标 | 事件 |
| --- | --- | --- |
| 当前已具备 | 建立可信问数基础漏斗 | 已实现的 11 类事件 |
| P0 | 证明三个差异化能力 | 预热应用、Bad Case 契约与关闭、Schema 影响与恢复 |
| P1 | 优化过程体验 | 预热编辑、Evidence 查看、明细查看、回归启动 |
| P2 | 扩展运营分析 | 导出、协作、订阅、长期留存与队列负载 |

优先级判断原则是：先记录能够证明产品价值和安全边界的事实，再补充页面行为与体验优化事件。

## 11. 当前实现对应关系

| 实现位置 | 当前作用 |
| --- | --- |
| `app/services/product_analytics.py` | 生成问数、用户价值和治理事件，汇总漏斗与质量指标 |
| `audit.product_event` | 保存隐私保护后的统一事件 |
| `audit.query_run` | 关联查询版本、血缘、成本和执行状态 |
| `/api/chatbi/operations/interactions` | 接收结果采用和人工修正的显式操作 |
| `/api/chatbi/operations/summary` | 输出指定窗口内的漏斗、质量、时延与治理汇总 |
| `frontend/app.js` | 在用户明确操作时请求记录价值事件 |

当前实现已经能够展示问数基础漏斗，但 AI 预热、Schema 变化和 Bad Case 的完整过程事件仍需要按 P0 方案补充，才能形成与产品差异化一致的分析闭环。
