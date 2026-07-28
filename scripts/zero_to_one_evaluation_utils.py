"""Shared provenance and scoring helpers for the current zero-to-one evaluation.

This module deliberately contains no legacy benchmark paths or executable CLI.
It is the single helper dependency for the frozen Dify preheat evaluator.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.models import Metric, MetricSemanticProfile, MetricVersion
from app.db.session import SessionLocal


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_CODE_PATHS = (
    ROOT / "app" / "services" / "query_policy.py",
    ROOT / "app" / "services" / "metric_retrieval.py",
    ROOT / "app" / "services" / "chatbi_entrypoint.py",
    ROOT / "app" / "services" / "dsl_validator.py",
    ROOT / "app" / "services" / "query_compiler.py",
)


def checksum(rows: list[dict[str, Any]]) -> str:
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def normalized_rows(body: dict[str, Any], case: dict[str, Any]) -> list[dict[str, Any]]:
    metric_id = case["metric_ids"][0]
    dimension_id = case["expected_result"].get("dimension_id")
    rows = []
    for source in (body.get("execution") or {}).get("rows", []):
        row: dict[str, Any] = {"value": round(float(source.get(metric_id) or 0), 2)}
        if dimension_id:
            row["dimension_value"] = str(source.get(dimension_id) or "")
        rows.append(row)
    if dimension_id:
        rows.sort(key=lambda row: row["dimension_value"])
    return rows


def evaluate_body(
    case: dict[str, Any], body: dict[str, Any], latency_ms: float
) -> dict[str, Any]:
    errors = []
    expected_status = case["expected_status"]
    observed_status = body.get("status")
    if observed_status != expected_status:
        errors.append(
            {"layer": "status", "expected": expected_status, "observed": observed_status}
        )
    if expected_status == "SUCCESS" and observed_status == "SUCCESS":
        expected_metric = case["metric_ids"][0]
        observed_metric = (body.get("selected_metric") or {}).get("metric_id")
        if observed_metric != expected_metric:
            errors.append(
                {"layer": "retrieval", "expected": expected_metric, "observed": observed_metric}
            )
        observed_checksum = checksum(normalized_rows(body, case))
        expected_checksum = case["expected_result"]["result_checksum_sha256"]
        if observed_checksum != expected_checksum:
            errors.append(
                {"layer": "execution", "expected": expected_checksum, "observed": observed_checksum}
            )
        reflection = (body.get("reflection") or {}).get("status")
        if reflection != "PASS":
            errors.append(
                {"layer": "reflection", "expected": "PASS", "observed": reflection}
            )
    unsafe_executed = expected_status != "SUCCESS" and (
        body.get("execution") or {}
    ).get("status") == "SUCCEEDED"
    if unsafe_executed:
        errors.append(
            {"layer": "safety", "expected": "not executed", "observed": "SUCCEEDED"}
        )
    return {
        "case_id": case["case_id"],
        "domain": case["domain"],
        "category": case["category"],
        "complexity_level": case["complexity"]["level"],
        "schema_perturbation": case["complexity"].get("schema_perturbation"),
        "expected_status": expected_status,
        "observed_status": observed_status,
        "passed": not errors,
        "unsafe_executed": unsafe_executed,
        "latency_ms": round(latency_ms, 3),
        "errors": errors,
    }


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def product_code_sha256() -> str:
    digest = hashlib.sha256()
    for path in PRODUCT_CODE_PATHS:
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def semantic_assets_sha256(business_domain_id: str) -> str:
    with SessionLocal() as session:
        metrics = session.scalars(
            select(Metric)
            .where(Metric.business_domain_id == business_domain_id)
            .order_by(Metric.id)
        ).all()
        payload = []
        for metric in metrics:
            if metric.status != "PUBLISHED":
                continue
            version = session.scalar(
                select(MetricVersion)
                .where(
                    MetricVersion.metric_id == metric.id,
                    MetricVersion.status == "PUBLISHED",
                )
                .order_by(MetricVersion.version.desc())
                .limit(1)
            )
            profile = session.get(MetricSemanticProfile, metric.id)
            payload.append(
                {
                    "metric_id": metric.id,
                    "version": version.version if version else None,
                    "name": metric.name,
                    "description": metric.description,
                    "aliases": sorted(row.alias for row in metric.aliases),
                    "positive_examples": sorted(
                        str(item)
                        for item in ((profile.positive_examples_json if profile else []) or [])
                    ),
                    "negative_examples": sorted(
                        str(item)
                        for item in ((profile.negative_examples_json if profile else []) or [])
                    ),
                }
            )
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def _apply_stability_checks(results: list[dict[str, Any]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        if result.get("repeat_group_id"):
            groups[result["repeat_group_id"]].append(result)
    for group_results in groups.values():
        checksums = {
            result["observed_checksum"]
            for result in group_results
            if result.get("observed_checksum")
        }
        if len(checksums) <= 1:
            continue
        for result in group_results:
            result["errors"].append(
                {
                    "layer": "stability",
                    "expected": "one checksum per repeat group",
                    "observed": len(checksums),
                }
            )
            result["passed"] = False


def _slice_summary(results: list[dict[str, Any]], key: str) -> dict[str, Any]:
    slices: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        slices[str(result.get(key))].append(result)
    return {
        name: {
            "cases": len(items),
            "passed": sum(item["passed"] for item in items),
            "pass_rate": round(sum(item["passed"] for item in items) / len(items), 6),
            "unsafe_execution_count": sum(item["unsafe_executed"] for item in items),
        }
        for name, items in sorted(slices.items())
    }


def _first_query_quality(results: list[dict[str, Any]]) -> dict[str, Any]:
    success_cases = [result for result in results if result["expected_status"] == "SUCCESS"]
    retrieval_ranks = [
        int(result["expected_candidate_rank"])
        for result in success_cases
        if result.get("expected_candidate_rank")
    ]
    direct_correct = sum(
        result.get("observed_status") == "SUCCESS"
        and result.get("selected_metric_id") == result.get("expected_metric_id")
        for result in success_cases
    )
    top1_correct = sum(
        result.get("expected_candidate_rank") == 1 for result in success_cases
    )
    recall_at_3 = sum(
        bool(result.get("expected_candidate_rank") and result["expected_candidate_rank"] <= 3)
        for result in success_cases
    )
    wrong_metric = sum(
        result.get("observed_status") == "SUCCESS"
        and bool(result.get("selected_metric_id"))
        and result.get("selected_metric_id") != result.get("expected_metric_id")
        for result in success_cases
    )
    direct_reject = sum(
        result.get("observed_status") == "REJECT" for result in success_cases
    )
    return {
        "answerable_cases": len(success_cases),
        "direct_correct": direct_correct,
        "direct_correct_rate": round(direct_correct / len(success_cases), 6)
        if success_cases
        else None,
        "top1_correct": top1_correct,
        "top1_accuracy": round(top1_correct / len(success_cases), 6)
        if success_cases
        else None,
        "recall_at_3_count": recall_at_3,
        "recall_at_3": round(recall_at_3 / len(success_cases), 6)
        if success_cases
        else None,
        "mrr": round(
            sum(1 / rank for rank in retrieval_ranks) / len(success_cases), 6
        )
        if success_cases
        else None,
        "wrong_metric_count": wrong_metric,
        "wrong_metric_rate": round(wrong_metric / len(success_cases), 6)
        if success_cases
        else None,
        "direct_reject_count": direct_reject,
        "direct_reject_rate": round(direct_reject / len(success_cases), 6)
        if success_cases
        else None,
        "retrieval_source_distribution": dict(
            Counter(
                source
                for result in success_cases
                for source in (result.get("retrieval_sources") or [])
            )
        ),
    }


def build_report(
    split: str,
    results: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    semantic_domain: str,
) -> dict[str, Any]:
    _apply_stability_checks(results)
    latencies = [result["latency_ms"] for result in results]
    passed = sum(result["passed"] for result in results)
    return {
        "benchmark_id": manifest["golden_set_id"],
        "split": split,
        "generated_at": datetime.now(UTC).isoformat(),
        "evidence_class": manifest["evidence_class"],
        "provenance": {
            "golden_set_id": manifest["golden_set_id"],
            "golden_sha256": manifest[f"{split}_sha256"],
            "product_code_sha256": product_code_sha256(),
            "snapshot_id": manifest["snapshot_id"],
            "single_run_locked_blind": False,
            "semantic_assets_sha256": semantic_assets_sha256(semantic_domain),
        },
        "summary": {
            "cases": len(results),
            "passed": passed,
            "pass_rate": round(passed / len(results), 6) if results else None,
            "unsafe_execution_count": sum(
                result["unsafe_executed"] for result in results
            ),
            "compiled_for_guarded_case_count": sum(
                result["compiled"]
                for result in results
                if result["expected_status"] in {"REJECT", "BLOCKED"}
            ),
            "status_distribution": dict(
                Counter(result["observed_status"] for result in results)
            ),
            "latency_p50_ms": round(statistics.median(latencies), 3)
            if latencies
            else None,
            "latency_p95_ms": round(percentile(latencies, 0.95) or 0, 3),
            "latency_max_ms": max(latencies) if latencies else None,
        },
        "first_query_quality": _first_query_quality(results),
        "by_category": _slice_summary(results, "category"),
        "by_complexity": _slice_summary(results, "complexity_level"),
        "by_expected_status": _slice_summary(results, "expected_status"),
        "cases": results,
        "claim_restriction": manifest["claim_restriction"],
    }
