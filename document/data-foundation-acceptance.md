# 数据底座验收记录

> 验收日期：2026-07-07
>
> 验收数据档位：`smoke`
>
> 固定随机种子：`20260707`

## 1. 基础设施

| 服务 | 镜像 | 状态 | 验收结果 |
| --- | --- | --- | --- |
| PostgreSQL | `postgres:16-alpine` | healthy | 通过 |
| ClickHouse | `clickhouse/clickhouse-server:25.8` | healthy | 通过 |
| Redis | `redis:7-alpine` | healthy | 通过 |

`docker compose config --quiet` 通过。

PostgreSQL 初始化 Schema：

```text
app
audit
metric_center
```

Redis 认证后返回 `PONG`。

## 2. 生成数据

生成范围：2025-07-01 至 2026-06-30。

| 数据集 | 行数 |
| --- | ---: |
| 销售订单商品 CSV | 7,223 |
| 广告投放日 CSV | 8,760 |

生成数据本地校验：

```text
PASS: sales rows, invariants, five metric baselines, and refund anomaly
PASS: ad rows, funnel invariants, ROAS baseline, and efficiency anomaly
```

## 3. ClickHouse 分层结果

| 表 | 行数 |
| --- | ---: |
| `ods_sales_order_item` | 7,223 |
| `dwd_sales_order_item` | 6,958 |
| `dws_sales_day` | 6,289 |
| `ods_ad_delivery_day` | 8,760 |
| `dws_ad_delivery_day` | 4,380 |

ODS 与 DWD 行数差异来自取消订单和测试订单清洗，符合设计。

加载脚本连续执行两次后行数和指标保持一致，幂等重建通过。

## 4. 核心指标

使用只读账号 `chatbi_reader` 查询 ClickHouse，并与生成 Manifest 对比：

| 指标 | ClickHouse 结果 | 单位 | 结果 |
| --- | ---: | --- | --- |
| GMV | 2,390,605.13 | CNY | PASS |
| 已支付销售额 | 2,209,107.48 | CNY | PASS |
| 支付订单量 | 4,822 | order | PASS |
| 毛利额 | 1,005,214.23 | CNY | PASS |
| 毛利率 | 47.13 | % | PASS |
| ROAS | 8.95 | multiple | PASS |

验收过程中发现 ClickHouse Decimal 直接相除导致比率小数位丢失，已在基准 SQL 中改为显式 `Float64` 除法并保留两位小数。后续 SQL Compiler 必须复用该规则。

## 5. 自动校验

以下检查均通过：

- 6 个 Python 脚本 AST 语法解析。
- Query DSL JSON Schema 和示例。
- OpenAPI 3.1 和 7 个 POST 路径。
- Dify 7 个 HTTP 节点与 OpenAPI 路径映射。
- 24 个唯一指标定义。
- 生成数据不变量及两个业务异常。
- 6 个 ClickHouse 指标基准。

## 6. 验收结论

数据底座 MVP 已达到进入指标中心开发的前置条件：

- 基础服务可启动。
- 数据可重复生成、清洗和聚合。
- 业务异常可验证。
- 指标有独立基准，不依赖 LLM 判断正确性。
- 只读查询账户可用。

当前验收只证明本机 smoke 档位闭环，不代表百万级性能已经验证。`demo` 和 `portfolio` 档位的性能报告应在查询服务和缓存完成后再执行。

