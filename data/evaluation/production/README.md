# 生产复杂度 0→1 预热评测资产

此目录只保留当前 0→1 冷启动预热评测的测试集、仓库合同和复现输入。历史 Olist、First Query、Production Evidence V2、Post-blind 与定向修复数据已清理。

## 保留资产

| 路径 | 作用 |
| --- | --- |
| `schema_contract.json` | 42 表、442 字段的生产模拟仓库合同 |
| `production_snapshot.json` | 已加载仓库的规模、DDL 哈希和完整性快照 |
| `case_schema.json` | 单条评测用例的通用结构说明 |
| `frontend_closure_v1/development.json` | 当前 1,128 条 Development 集 |
| `frontend_closure_v1/regression.json` | 当前 470 条 Regression 集 |
| `frontend_closure_v1/locked_blind.json` | 当前 752 条历史 Locked 集；由于曾被使用，不再声称是真盲测 |
| `frontend_closure_v1/manifest.json` | 三个 split 的数量与哈希清单 |
| `frontend_closure_v1/capability_profiles/cross_fact_v1.json` | 已发布跨事实能力的期望覆盖与 Oracle 来源 |

## 0→1 复现流程

以下流程会清空生产域治理和历史闭环状态。执行重置前必须明确提供确认参数：

```bash
.venv/bin/python -m scripts.reset_zero_to_one --confirm ZERO_TO_ONE_RESET
.venv/bin/python -m scripts.bootstrap_zero_to_one_governance
.venv/bin/python -m scripts.apply_zero_to_one_ai_preheat
.venv/bin/python -m scripts.freeze_zero_to_one_preheat
.venv/bin/python -m scripts.evaluate_dify_preheat \
  --run-label <new-unique-run-label> \
  --capability-profile cross_fact_v1 \
  --prioritize-capability-cases \
  --batch-size 25 \
  --workers 4
```

评测前必须确保 PostgreSQL、ClickHouse、本地 DataPath 服务和已发布的 Dify 工作流可访问。

## 当前证据

2026-07-19 的原始 1,200 条 Development 历史结果位于：

- `reports/dify-preheat/zero-to-one-20260719/development.json`
- `reports/dify-preheat/zero-to-one-20260719/development.md`
- `reports/zero-to-one/zero-to-one-development-report.md`

原始结果为 1,118/1,200（93.17%），危险执行为 0。2026-07-27 起，已移除不属于当前产品范围的 150 条 `dirty_data` 样本，现行 Development 为 1,128 条。根据原始逐条结果对相同样本子集重算为 1,118/1,128（99.11%），但代码变更后的正式新成绩仍应通过新的完整评测产生。

上述报告是 2026-07-19 的不可变历史证据。仓库清理后，旧实验数据文件已删除、产品代码哈希也已变化，因此不能从已有 checkpoint 继续运行或声称复现同一构建；新评测必须使用新的 `--run-label`，并生成新的代码、数据集和语义资产哈希。保留 split 文件及 manifest 的哈希仍可验证当前测试集本身未被改写。

当前测评不覆盖数据质量审计策略；这类问题由独立的数据质量治理职责处理，不计入当前 ChatBI 语义准确率。
