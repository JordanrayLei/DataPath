# 数据底座设计与运行说明

> 阶段：作品集 MVP 数据底座
>
> 数据范围：2025-07-01 至 2026-06-30
>
> 业务域：电商经营、广告投放

## 1. 组件职责

| 组件 | 职责 | 暴露端口 |
| --- | --- | ---: |
| PostgreSQL 16 | 指标、语义模型、版本、会话和审计元数据 | 5432 |
| ClickHouse 25.8 | ODS/DWD/DWS 数据与在线分析查询 | 8123 / 9000 |
| Redis 7 | 查询状态、幂等、缓存和限流 | 6379 |

组件版本在 `compose.yaml` 中固定主次版本。示例密码仅用于本地开发，可通过 `.env` 覆盖。

## 2. ClickHouse 分层

```text
ods_sales_order_item ──→ dwd_sales_order_item ──→ dws_sales_day
ods_ad_delivery_day  ──→ dwd_ad_delivery_day  ──→ dws_ad_delivery_day
```

### 2.1 ODS

ODS 保存可重新加工的模拟业务数据，保留取消订单和测试订单，以验证清洗规则。

### 2.2 DWD

销售 DWD：

- 排除测试和取消订单。
- 以支付日期作为当前经营指标时间口径。
- 固化 `net_revenue = paid_amount - refund_amount`。
- 固化 `gross_profit = paid_amount - refund_amount - recognized_item_cost`。

广告 DWD 保留日期、平台、账户、计划、素材、设备、归因窗口和漏斗指标。

### 2.3 DWS

- 销售按日期、地区、省份、渠道和品类聚合。
- 订单量保存为 `uniqExactState`，避免跨维度简单求和导致重复计数。
- 广告按日期、平台、账户、计划、设备和归因窗口聚合。

在线 Compiler 可以根据查询粒度选择 DWS；不兼容时回退到 DWD。

## 3. 数据生成器

`scripts/generate_demo_data.py` 使用固定随机种子 `20260707`，相同参数会生成相同指标结果。

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --profile smoke
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --profile demo
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --profile portfolio
```

也可覆盖订单数：

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --profile smoke --orders 20000
```

生成文件默认写入 `data/generated/`，不会提交 Git：

```text
sales_order_items.csv
ad_delivery_daily.csv
manifest.json
```

Manifest 保存行数、固定种子、日期范围、指标基准和预置异常结果。

## 4. 预置业务事件

### 4.1 销售异常

2026 年 3 月，华东地区数码品类退款概率显著提升。验证脚本要求该切片金额退款率至少是其他数码订单的 2 倍。

可演示问题：

```text
2026 年各月数码品类退款率趋势如何？
3 月哪个地区的退款异常最明显？
华东数码退款上升对毛利率有什么影响？
```

### 4.2 广告异常

2026 年 4 月，`CMP_EAST_GROWTH` 计划 CPC 上升且 CVR 下降。验证脚本要求 4 月 ROAS 低于该计划 3 月 ROAS 的 60%。

可演示问题：

```text
最近一年各广告计划 ROAS 趋势如何？
4 月哪个计划投放效率下降最多？
华东新客增长计划的成本和转化发生了什么变化？
```

这些是可验证的相关性事件，不构成真实因果证据。AI 解读不得断言唯一原因。

## 5. 启动与加载

### 5.1 启动依赖

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up -d
docker compose ps
```

### 5.2 生成并验证数据

```powershell
.\.venv\Scripts\python.exe scripts\generate_demo_data.py --profile smoke
.\.venv\Scripts\python.exe scripts\validate_generated_data.py
```

### 5.3 加载 ClickHouse

```powershell
.\.venv\Scripts\python.exe scripts\load_clickhouse_data.py
```

加载脚本会：

1. 确认 ClickHouse 健康。
2. 幂等应用表结构。
3. 清空并重新加载 ODS。
4. 重建 DWD 和 DWS。

### 5.4 指标验收

```powershell
.\.venv\Scripts\python.exe scripts\verify_clickhouse_metrics.py
```

验证脚本使用只读 `chatbi_reader`，对比：

- GMV。
- 已支付销售额。
- 支付订单量。
- 毛利额。
- 毛利率。
- ROAS。

基准 SQL 位于 `sql/baseline_metrics.sql`。

## 6. 数据质量规则

生成数据验证包括：

- 金额不得为负。
- 退款金额不得超过支付金额。
- 取消订单不得存在支付时间和支付金额。
- `conversions <= clicks <= impressions`。
- Manifest 行数与 CSV 一致。
- 6 个核心指标与重新计算结果一致。
- 两个预置异常必须达到最小显著程度。

## 7. 本地账号

| 系统 | 用户 | 密码 | 权限 |
| --- | --- | --- | --- |
| PostgreSQL | `data_agent` | `data_agent_dev` | 本地开发管理 |
| ClickHouse | `data_agent` | `data_agent_dev` | 本地数据加载管理 |
| ClickHouse | `chatbi_reader` | `chatbi_reader_dev` | `data_warehouse.*` 只读 |
| Redis | - | `data_agent_dev` | 本地缓存访问 |

这些凭证不得用于任何公网或生产环境。

## 8. 已知边界

- 当前数据是确定性模拟数据，不代表真实企业数据规模和分布。
- ODS 直接从 CSV 加载，尚未接入真实 CDC 或业务数据库。
- 当前只实现 ClickHouse Adapter 所需数据结构。
- dbt 和 Airflow 尚未接入；本阶段先用确定性 SQL 证明分层和指标闭环。
- PostgreSQL 当前只初始化 Schema，指标实体表将在下一阶段实现。
- 容器配置面向单机作品集，不是高可用部署方案。

## 9. 下一阶段接口

以下最小垂直链已于 2026-07-07 实现并通过真实 HTTP smoke：

```text
context/load
→ metrics/retrieve
→ dsl/validate
→ query/compile
→ query/execute
```

Profiler 和 Reflection 在真实查询闭环稳定后接入。
