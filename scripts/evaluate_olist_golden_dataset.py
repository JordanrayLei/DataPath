"""Run the Olist golden set through the public ChatBI entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "evaluation" / "golden"
DEFAULT_REPORTS = ROOT / "reports"
SPLITS = ("development", "regression", "blind")


def _load_cases(split: str) -> list[dict[str, Any]]:
    return json.loads(
        (GOLDEN / f"olist_golden_{split}.json").read_text(encoding="utf-8")
    )


def _error(
    errors: list[dict[str, Any]], layer: str, code: str, expected: Any, observed: Any
) -> None:
    errors.append(
        {"layer": layer, "code": code, "expected": expected, "observed": observed}
    )


def _candidate_count(body: dict[str, Any]) -> int:
    metric_ids = {
        candidate.get("metric_id")
        for mention in (body.get("retrieval") or {}).get("mentions", [])
        for candidate in mention.get("candidates", [])
        if candidate.get("metric_id")
    }
    return len(metric_ids)


def _normalized_rows(
    body: dict[str, Any], case: dict[str, Any]
) -> list[dict[str, Any]]:
    execution = body.get("execution") or {}
    metric_id = case["expected_metric_id"]
    dimensions = case.get("expected_dimensions", [])
    rows = []
    for source in execution.get("rows", []):
        row: dict[str, Any] = {"value": source.get(metric_id)}
        if dimensions:
            row["dimension_value"] = source.get(dimensions[0])
        rows.append(row)
    if dimensions:
        rows.sort(key=lambda row: str(row.get("dimension_value")))
    return rows


def _checksum(rows: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _close(observed: Any, expected: Any, tolerance: float) -> bool:
    try:
        return math.isclose(
            float(observed), float(expected), abs_tol=tolerance, rel_tol=1e-9
        )
    except (TypeError, ValueError):
        return False


def _assert_success(
    case: dict[str, Any], body: dict[str, Any], errors: list[dict[str, Any]]
) -> None:
    selected = body.get("selected_metric") or {}
    dsl = body.get("dsl") or {}
    compiled = body.get("compiled") or {}
    execution = body.get("execution") or {}
    reflection = body.get("reflection") or {}

    expected_metric = case.get("expected_metric_id")
    if expected_metric and selected.get("metric_id") != expected_metric:
        _error(errors, "retrieval", "metric_id", expected_metric, selected.get("metric_id"))

    observed_time_range = dsl.get("time_range") or {}
    comparable_time_range = {
        key: observed_time_range.get(key) for key in ("start", "end")
    }
    checks = (
        ("intent", case.get("expected_intent"), dsl.get("intent")),
        ("query_mode", case.get("expected_query_mode"), dsl.get("query_mode")),
        ("time_range", case.get("expected_time_range"), comparable_time_range),
    )
    for code, expected, observed in checks:
        if expected is not None and observed != expected:
            _error(errors, "query_understanding", code, expected, observed)

    if "expected_dimensions" in case:
        observed_dimensions = [
            item.get("dimension_id") for item in dsl.get("dimensions", [])
        ]
        if observed_dimensions != case["expected_dimensions"]:
            _error(
                errors,
                "query_understanding",
                "dimensions",
                case["expected_dimensions"],
                observed_dimensions,
            )

    expected_models = set(case.get("expected_models", []))
    observed_models = set((compiled.get("lineage") or {}).get("models", []))
    if expected_models and not expected_models.issubset(observed_models):
        _error(
            errors,
            "join_planning",
            "lineage_models",
            sorted(expected_models),
            sorted(observed_models),
        )

    if execution.get("status") != "SUCCEEDED":
        _error(errors, "execution", "status", "SUCCEEDED", execution.get("status"))
        return

    oracle = case.get("result_assertions")
    if oracle:
        rows = _normalized_rows(body, case)
        tolerance = float(oracle.get("numeric_tolerance", 0.01))
        if execution.get("row_count") != oracle["row_count"]:
            _error(
                errors,
                "execution",
                "row_count",
                oracle["row_count"],
                execution.get("row_count"),
            )
        observed_checksum = _checksum(rows)
        if observed_checksum != oracle["result_checksum_sha256"]:
            _error(
                errors,
                "execution",
                "result_checksum",
                oracle["result_checksum_sha256"],
                observed_checksum,
            )
        values = [float(row.get("value") or 0) for row in rows]
        total = sum(values)
        if not _close(total, oracle["total_value"], tolerance):
            _error(errors, "execution", "total_value", oracle["total_value"], total)
        if rows:
            top = max(rows, key=lambda row: float(row.get("value") or 0))
            if oracle.get("top_dimension") is not None and str(
                top.get("dimension_value")
            ) != str(oracle["top_dimension"]):
                _error(
                    errors,
                    "execution",
                    "top_dimension",
                    oracle["top_dimension"],
                    top.get("dimension_value"),
                )
            if not _close(top.get("value"), oracle["top_value"], tolerance):
                _error(
                    errors,
                    "execution",
                    "top_value",
                    oracle["top_value"],
                    top.get("value"),
                )

    expected_reflection = case.get("expected_reflection_status")
    if expected_reflection and reflection.get("status") != expected_reflection:
        _error(
            errors,
            "reflection",
            "status",
            expected_reflection,
            reflection.get("status"),
        )


def evaluate_case(
    client: TestClient,
    case: dict[str, Any],
    run_id: str,
    conversation_ids: dict[str, str],
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    source_conversation = case.get("conversation_id") or case["case_id"]
    conversation_id = conversation_ids.setdefault(
        source_conversation, f"golden_{run_id}_{source_conversation}"[:128]
    )
    payload = {
        "query": case["query"],
        "workspace_id": case.get("workspace_id", "demo"),
        "conversation_id": conversation_id,
        "biz_domain": "auto",
        "timezone": "Asia/Shanghai",
    }
    started = time.perf_counter()
    try:
        response = client.post("/api/chatbi/ask", json=payload)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        if response.status_code != 200:
            body: dict[str, Any] = {"http_body": response.text[:2000]}
            _error(errors, "transport", "http_status", 200, response.status_code)
        else:
            body = response.json()
    except Exception as exc:  # The report must retain infrastructure failures.
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        body = {"exception": f"{type(exc).__name__}: {exc}"}
        _error(errors, "transport", "exception", None, body["exception"])

    observed_status = body.get("status")
    if observed_status != case["expected_status"]:
        _error(
            errors,
            "status_gate",
            "status",
            case["expected_status"],
            observed_status,
        )

    if observed_status == "SUCCESS":
        _assert_success(case, body, errors)
    elif observed_status == "CLARIFY" and case["expected_status"] == "CLARIFY":
        minimum = case.get("expected_candidate_count_min")
        observed = _candidate_count(body)
        if minimum is not None and observed < minimum:
            _error(errors, "retrieval", "candidate_count", f">={minimum}", observed)

    if case.get("must_not_compile") and body.get("compiled") is not None:
        _error(errors, "safety", "compiled", None, "present")
    if case.get("must_not_execute") and body.get("execution") is not None:
        _error(errors, "safety", "executed", None, "present")
    if case.get("inherit_context") and observed_status == "SUCCESS":
        context_detail = next(
            (
                step.get("detail", "")
                for step in body.get("steps", [])
                if step.get("key") == "context"
            ),
            "",
        )
        if "已继承上一轮" not in context_detail:
            _error(errors, "memory", "context_inherited", True, context_detail)
    if case.get("must_not_leak_sql"):
        serialized = json.dumps(body, ensure_ascii=False)
        if re.search(r"\bSELECT\s+", serialized, flags=re.IGNORECASE):
            _error(errors, "safety", "raw_sql_leak", False, True)

    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "category": case["category"],
        "query": case["query"],
        "expected_status": case["expected_status"],
        "observed_status": observed_status,
        "passed": not errors,
        "latency_ms": latency_ms,
        "errors": errors,
        "trace_id": body.get("trace_id"),
        "query_id": (body.get("compiled") or {}).get("query_id"),
    }


def _rate(passed: int, total: int) -> float:
    return round(passed / total, 4) if total else 0.0


def _group_summary(results: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result[key]].append(result)
    return {
        name: {
            "total": len(items),
            "passed": sum(item["passed"] for item in items),
            "pass_rate": _rate(sum(item["passed"] for item in items), len(items)),
        }
        for name, items in sorted(grouped.items())
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(item["passed"] for item in results)
    latencies = [item["latency_ms"] for item in results]
    layer_failures = Counter(
        error["layer"] for item in results for error in item["errors"]
    )
    error_codes = Counter(
        f"{error['layer']}.{error['code']}"
        for item in results
        for error in item["errors"]
    )
    confusion = Counter(
        f"{item['expected_status']} -> {item['observed_status']}" for item in results
    )
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": _rate(passed, len(results)),
        "by_split": _group_summary(results, "split"),
        "by_category": _group_summary(results, "category"),
        "layer_failure_counts": dict(layer_failures.most_common()),
        "error_code_counts": dict(error_codes.most_common()),
        "status_confusion": dict(confusion.most_common()),
        "latency_ms": {
            "average": round(statistics.fmean(latencies), 2) if latencies else 0,
            "p50": round(statistics.median(latencies), 2) if latencies else 0,
            "p95": round(sorted(latencies)[math.ceil(len(latencies) * 0.95) - 1], 2)
            if latencies
            else 0,
            "max": round(max(latencies), 2) if latencies else 0,
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# DataPath Olist 黄金集评测报告",
        "",
        f"- 评测时间：{report['evaluated_at']}",
        f"- 评测范围：{', '.join(report['requested_splits'])}",
        f"- 严格通过率：**{summary['passed']}/{summary['total']} ({summary['pass_rate']:.2%})**",
        f"- 延迟：平均 {summary['latency_ms']['average']} ms，P95 {summary['latency_ms']['p95']} ms",
        "- 判定规则：状态、指标、意图、时间、维度、查询模式、模型血缘、执行结果、Reflection、上下文与安全门禁必须全部通过。",
        "- 限制：接口不返回 Join Relation ID，本报告验证模型血缘和独立 SQL Oracle，不宣称已直接验证关系 ID。",
        "- 多轮限制：当前多轮集只验证连续成功、上下文继承标记和 SQL 不泄露，尚未配置逐轮结果 Oracle。",
        "",
        "## 分测试集结果",
        "",
        "| 测试集 | 通过 | 总数 | 通过率 |",
        "|---|---:|---:|---:|",
    ]
    for name, item in summary["by_split"].items():
        lines.append(f"| {name} | {item['passed']} | {item['total']} | {item['pass_rate']:.2%} |")
    lines.extend(
        [
            "",
            "## 分能力结果",
            "",
            "| 能力类型 | 通过 | 总数 | 通过率 |",
            "|---|---:|---:|---:|",
        ]
    )
    for name, item in summary["by_category"].items():
        lines.append(f"| {name} | {item['passed']} | {item['total']} | {item['pass_rate']:.2%} |")
    lines.extend(
        [
            "",
            "## 失败层分布",
            "",
            "| 层级 | 断言失败数 |",
            "|---|---:|",
        ]
    )
    for name, count in summary["layer_failure_counts"].items():
        lines.append(f"| {name} | {count} |")
    if not summary["layer_failure_counts"]:
        lines.append("| 无 | 0 |")
    lines.extend(
        [
            "",
            "## 主要失败模式",
            "",
            "| 错误码 | 次数 |",
            "|---|---:|",
        ]
    )
    for name, count in list(summary["error_code_counts"].items())[:15]:
        lines.append(f"| {name} | {count} |")
    if not summary["error_code_counts"]:
        lines.append("| 无 | 0 |")
    lines.extend(["", "## Bad Case 样例", ""])
    failed = [item for item in report["results"] if not item["passed"]]
    for item in failed[:30]:
        signature = ", ".join(
            f"{error['layer']}.{error['code']}" for error in item["errors"]
        )
        lines.append(
            f"- `{item['case_id']}` [{item['category']}] {item['query']}：{signature}"
        )
    if len(failed) > 30:
        lines.append(f"- 其余 {len(failed) - 30} 条见 JSON 明细。")
    if not failed:
        lines.append("- 无。")
    lines.extend(
        [
            "",
            "## 状态门禁混淆",
            "",
            "| 期望 -> 实际 | 数量 |",
            "|---|---:|",
        ]
    )
    for name, count in summary["status_confusion"].items():
        lines.append(f"| {name} | {count} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--split", choices=("all", *SPLITS), default="all", help="Golden split to run"
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--report-name", default="olist-expanded-metrics-regression")
    args = parser.parse_args()

    requested_splits = list(SPLITS) if args.split == "all" else [args.split]
    cases = [case for split in requested_splits for case in _load_cases(split)]
    if args.limit is not None:
        cases = cases[: args.limit]
    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    results = []
    conversation_ids: dict[str, str] = {}
    with TestClient(app) as client:
        for index, case in enumerate(cases, 1):
            results.append(evaluate_case(client, case, run_id, conversation_ids))
            if index % 25 == 0 or index == len(cases):
                passed = sum(item["passed"] for item in results)
                print(f"[{index}/{len(cases)}] strict_pass={passed}/{index}", flush=True)

    report = {
        "report_version": "1.0",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "requested_splits": requested_splits,
        "golden_manifest": json.loads(
            (GOLDEN / "olist_golden_manifest.json").read_text(encoding="utf-8")
        ),
        "summary": summarize(results),
        "results": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{args.report_name}.json"
    markdown_path = args.output_dir / f"{args.report_name}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Reports: {json_path} and {markdown_path}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
