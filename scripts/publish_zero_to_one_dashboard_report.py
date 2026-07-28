"""Publish the frozen 0→1 evidence in the frontend evaluation-report schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT / "reports" / "dify-preheat" / "zero-to-one-20260719" / "development.json"
)
DEFAULT_OUTPUT = ROOT / "reports" / "chatbi-entrypoint-evaluation-latest.json"

CATEGORY_NAMES = {
    "core_metric": "核心指标",
    "cross_fact_join": "跨事实查询",
    "grain_and_fanout": "粒度与扇出",
    "multi_turn": "多轮上下文",
    "performance": "性能与重复稳定性",
    "permission": "权限",
    "schema_change": "Schema 变化",
    "scope_safety": "范围安全",
    "semantic_ambiguity": "语义歧义",
    "time_and_window": "时间与窗口",
}
EXCLUDED_CATEGORIES = {"dirty_data"}
CURRENT_BENCHMARK_ID = "datapath-frontend-editable-closure-2350-v2"


def build_dashboard_report(source: dict[str, Any]) -> dict[str, Any]:
    source_summary = source["summary"]
    categories = {
        category: result
        for category, result in (source.get("by_category") or {}).items()
        if category not in EXCLUDED_CATEGORIES
    }
    total = sum(int(result.get("cases") or 0) for result in categories.values())
    passed = sum(int(result.get("passed") or 0) for result in categories.values())
    unsafe = int(source_summary.get("unsafe_execution_count") or 0)
    quality = source.get("first_query_quality") or {}
    latencies = [
        float(item["latency_ms"])
        for item in (source.get("cases") or [])
        if (
            isinstance(item, dict)
            and item.get("category") not in EXCLUDED_CATEGORIES
            and item.get("latency_ms") is not None
        )
    ]
    cases = []
    for category, result in categories.items():
        category_total = int(result.get("cases") or 0)
        category_passed = int(result.get("passed") or 0)
        failed = category_total - category_passed
        cases.append(
            {
                "name": CATEGORY_NAMES.get(category, category),
                "passed": failed == 0,
                "status": f"{category_passed}/{category_total}",
                "selected_metric_id": "分类汇总",
                "dsl_intent": "0→1 冷启动",
                "chart_type": "-",
                "latency_ms": None,
                "errors": [] if failed == 0 else [f"未通过 {failed} 条"],
            }
        )

    gates = [
        {
            "name": "危险执行为零",
            "passed": unsafe == 0,
            "detail": f"unsafe_execution_count={unsafe}",
        },
        {
            "name": "错误指标选择为零",
            "passed": int(quality.get("wrong_metric_count") or 0) == 0,
            "detail": f"wrong_metric_count={int(quality.get('wrong_metric_count') or 0)}",
        },
        {
            "name": "评测证据已冻结",
            "passed": bool(source.get("protocol") and source.get("provenance")),
            "detail": "展示当前 Development 测评范围内的冻结逐条证据。",
        },
    ]
    return {
        "report_name": "zero-to-one-development-current-scope-v2",
        "generated_at": source.get("generated_at"),
        "target": f"0→1 冷启动预热 Development（{total:,} 条）",
        "summary": {
            "status": "FROZEN_EVIDENCE",
            "passed": passed,
            "total": total,
            "pass_rate": round(passed / total, 6) if total else 0.0,
            "avg_latency_ms": (
                round(sum(latencies) / len(latencies), 1) if latencies else None
            ),
            "case_passed": sum(1 for item in cases if item["passed"]),
            "case_total": len(cases),
            "gate_passed": sum(1 for item in gates if item["passed"]),
            "gate_total": len(gates),
        },
        "cases": cases,
        "gates": gates,
        "source_evidence": {
            "benchmark_id": CURRENT_BENCHMARK_ID,
            "derived_from_benchmark_id": source.get("benchmark_id"),
            "split": source.get("split"),
            "evidence_class": source.get("evidence_class"),
            "claim_restriction": source.get("claim_restriction"),
            "strict_result": {"passed": passed, "total": total},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    report = build_dashboard_report(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
