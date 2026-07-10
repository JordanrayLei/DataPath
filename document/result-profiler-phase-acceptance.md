# Result Profiler 与 Evidence 阶段验收

> 验收日期：2026-07-08
>
> 接口：`POST /api/chatbi/result/profile`

## 1. 实现内容

Result Profiler 使用确定性程序生成：

- Headline 指标。
- 首末周期趋势及变化率。
- 基于总体标准差的 z-score 异常点。
- 可加指标的维度贡献度及占比。
- 前端可直接消费的 Chart Spec。
- 与上述结论逐一绑定的强类型 Evidence。

Profiler 不调用 LLM，也不接收 SQL。

## 2. 信任边界

Dify 请求仍携带 `execution_result`，但后端只用它校验 Query ID 和请求结构。实际画像数据从 PostgreSQL `audit.query_run.result_json` 读取。

测试将请求首行 GMV 篡改为 `999999999`，Profile 结果未使用该值，证明 Dify 回传结果不是数据权威源。

Profile 同时校验：

- Query Run 存在且状态为 `SUCCEEDED`。
- Workspace 与 Query Run 一致。
- 请求 DSL Hash 与编译时 DSL Hash 一致。
- Query ID 与执行结果一致。

## 3. Evidence Schema

每条 Evidence 包含：

```text
evidence_id
evidence_type
statement
metric_id
metric_version
value
unit
time_range
dimensions
comparison
query_id
calculation
row_refs
```

`row_refs` 指向服务端查询结果的源行序号；`calculation` 描述确定性计算方法。Evidence ID 基于 Profile、类型、指标和业务区分项生成稳定摘要。

## 4. 审计存储

新增 Alembic Revision：`a30c62ebbc5d_add_result_profiles_and_evidence.py`。

新增表：

- `audit.result_profile`：每个 Query ID 一个幂等 Profile。
- `audit.evidence`：逐条保存指标、版本、值、单位、时间、维度、比较、计算方法和源行号。

重复请求同一 Query ID 返回相同 Profile ID 和 Evidence，不重复写入。

## 5. 计算规则

### Headline

- 有时间维度：使用最新时间桶；可加指标在桶内求和。
- 单行结果：直接使用该行。
- 无时间维度的可加指标：对返回维度行求和。
- 比率存在多维度时不做错误加权，返回 Caveat。

### Trend

- 至少两个时间桶才生成。
- 保存起点、终点、绝对变化、变化率、方向和点数。
- 分母为 0 时变化率返回 `null`。

### Anomaly

- 使用时间桶序列的总体 z-score。
- 阈值为 `abs(z) >= 2.0`。
- 这是统计异常信号，不是业务原因或因果结论。

### Contribution

- 仅对 amount/count 可加指标计算。
- 有时间维度时使用最新时间桶。
- Share 为维度值金额或数量占当前比较范围总值的比例。
- MVP 返回 Top5。

## 6. 图表规则

| 查询形态 | 图表 |
| --- | --- |
| 时间维度 | `line` |
| 单分类维度 | `bar` |
| 多分类维度 | `grouped_bar` |
| 无维度 | `metric` |
| 空结果 | `table` |

## 7. 测试结果

集成测试：

```text
6 passed
```

新增覆盖：

- Dify 回传结果被篡改时仍使用服务端结果。
- 12个月趋势生成 Headline、Trend、Chart 和 Evidence。
- Profile 重复请求幂等。
- Profile 与 Evidence 独立落库。
- 地区贡献度返回4个地区，排名为1～4，占比合计为100%。

真实 Uvicorn HTTP smoke：

```text
PASS: result/profile (3 evidence records; deterministic chart)
```

## 8. 已知边界

- 当前 z-score 是基础统计异常检测，未处理季节性和节假日基线。
- 比率跨维度缺少分子分母时不进行错误加权聚合。
- 大结果仍由 Dify 直接传入请求结构，尚未实现 `result_ref`。
- Dify 画布尚未用 `profile_ok` 做 fail-closed 门控。
- Reflection Validator 已在后续阶段实现；Dify 画布尚未完成解释与核验闭环联调。

## 9. 验收结论

Result Profiler 和强类型 Evidence 已达到验收标准，并已被后续 Reflection Validator 使用。当前仍不能声称完整 Dify ChatBI 已完成。
