from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports"
HISTORY_DIR = REPORTS_DIR / "evaluation-history"
DEFAULT_REPORT_CANDIDATES = [
    "chatbi-entrypoint-evaluation-live-8010",
    "chatbi-entrypoint-evaluation-latest",
]


class EvaluationReportError(ValueError):
    pass


def safe_report_path(report_name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", report_name):
        raise EvaluationReportError("report_name is invalid")
    path = (REPORTS_DIR / f"{report_name}.json").resolve()
    reports_root = REPORTS_DIR.resolve()
    if reports_root not in path.parents:
        raise EvaluationReportError("report path is outside reports directory")
    return path


def choose_report_path(report_name: str | None = None) -> tuple[str, Path]:
    if report_name:
        path = safe_report_path(report_name)
        if not path.exists():
            raise EvaluationReportError("report does not exist")
        return report_name, path

    for candidate in DEFAULT_REPORT_CANDIDATES:
        path = safe_report_path(candidate)
        if path.exists():
            return candidate, path
    raise EvaluationReportError("no evaluation report exists")


def read_report_json(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise EvaluationReportError("report JSON is invalid") from error

    if not isinstance(report, dict):
        raise EvaluationReportError("report JSON must be an object")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise EvaluationReportError("report summary is missing")
    return report


def load_evaluation_report(report_name: str | None = None) -> dict[str, Any]:
    selected_name, path = choose_report_path(report_name)
    report = read_report_json(path)
    summary = report["summary"]
    return {
        "status": "SUCCESS",
        "report_name": selected_name,
        "source_file": str(path),
        "generated_at": report.get("generated_at"),
        "target": report.get("target"),
        "summary": summary,
        "cases": report.get("cases") or [],
        "gates": report.get("gates") or [],
    }


def iter_evaluation_report_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved.exists() and resolved not in seen:
            seen.add(resolved)
            paths.append(resolved)

    for candidate in DEFAULT_REPORT_CANDIDATES:
        add(safe_report_path(candidate))
    for path in REPORTS_DIR.glob("chatbi-entrypoint-evaluation-*.json"):
        add(path)
    if HISTORY_DIR.exists():
        for path in HISTORY_DIR.glob("chatbi-entrypoint-evaluation-*.json"):
            add(path)
    return paths


def number_or_zero(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def report_to_trend_item(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    cases = report.get("cases") or []
    gates = report.get("gates") or []
    latencies = [
        number_or_zero(item.get("latency_ms"))
        for item in cases
        if isinstance(item, dict) and item.get("latency_ms") is not None
    ]
    failed_cases = [
        str(item.get("name") or "-")
        for item in cases
        if isinstance(item, dict) and not item.get("passed")
    ]
    failed_gates = [
        str(item.get("name") or "-")
        for item in gates
        if isinstance(item, dict) and not item.get("passed")
    ]
    total = int(number_or_zero(summary.get("total")))
    passed = int(number_or_zero(summary.get("passed")))
    pass_rate = number_or_zero(summary.get("pass_rate"))
    if total and not pass_rate:
        pass_rate = passed / total

    return {
        "snapshot_name": path.stem,
        "report_name": str(report.get("report_name") or path.stem),
        "source_file": str(path),
        "generated_at": report.get("generated_at"),
        "target": report.get("target"),
        "status": summary.get("status"),
        "passed": passed,
        "total": total,
        "pass_rate": round(pass_rate, 4),
        "case_passed": int(number_or_zero(summary.get("case_passed"))),
        "case_total": int(number_or_zero(summary.get("case_total"))),
        "gate_passed": int(number_or_zero(summary.get("gate_passed"))),
        "gate_total": int(number_or_zero(summary.get("gate_total"))),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "failed_cases": failed_cases,
        "failed_gates": failed_gates,
    }


def load_evaluation_trends(limit: int = 20) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise EvaluationReportError("limit must be between 1 and 100")

    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in iter_evaluation_report_paths():
        try:
            report = read_report_json(path)
        except EvaluationReportError:
            continue
        item = report_to_trend_item(path, report)
        key = (
            str(item.get("generated_at") or path.stat().st_mtime_ns),
            str(item.get("target") or ""),
            str(item.get("report_name") or item["snapshot_name"]),
        )
        if key not in deduped or HISTORY_DIR.resolve() in path.resolve().parents:
            deduped[key] = item

    items = list(deduped.values())
    items.sort(key=lambda item: (str(item.get("generated_at") or ""), item["snapshot_name"]))
    limited_items = items[-limit:]
    return {
        "status": "SUCCESS",
        "total": len(items),
        "limit": limit,
        "items": limited_items,
        "latest": limited_items[-1] if limited_items else None,
    }
