"""Import failed golden cases into the Bad Case board and write a review ledger."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.db.models import UserFeedback
from app.db.session import SessionLocal


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "olist-expanded-metrics-regression.json"
DEFAULT_OUTPUT = ROOT / "data" / "evaluation" / "badcases"


def classify_badcase(result: dict[str, Any]) -> dict[str, str]:
    category = result["category"]
    expected = result["expected_status"]
    observed = result.get("observed_status")
    if category == "semantic_robustness":
        return {
            "cluster": "retrieval_recall",
            "feedback_type": "METRIC_WRONG",
            "priority": "P1",
            "severity": "HIGH",
            "owner": "AI_RETRIEVAL",
        }
    if category == "ambiguity":
        return {
            "cluster": "ambiguity_gate",
            "feedback_type": "OTHER",
            "priority": "P1",
            "severity": "HIGH",
            "owner": "QUERY_UNDERSTANDING",
        }
    if expected == "BLOCKED":
        return {
            "cluster": "safety_action_classification",
            "feedback_type": "OTHER",
            "priority": "P2",
            "severity": "MEDIUM",
            "owner": "SAFETY_GATE",
        }
    return {
        "cluster": "scope_gate",
        "feedback_type": "OTHER",
        "priority": "P2",
        "severity": "MEDIUM",
        "owner": "QUERY_UNDERSTANDING",
    }


def build_badcases(report: dict[str, Any], report_path: Path) -> list[dict[str, Any]]:
    badcases = []
    for result in report["results"]:
        if result["passed"]:
            continue
        classification = classify_badcase(result)
        case_id = result["case_id"]
        expected = result["expected_status"]
        observed = result.get("observed_status")
        badcases.append(
            {
                "feedback_id": f"fb_golden_{case_id.lower()}",
                "case_id": case_id,
                "split": result["split"],
                "category": result["category"],
                "query": result["query"],
                "expected_status": expected,
                "observed_status": observed,
                "error_codes": [
                    f"{item['layer']}.{item['code']}" for item in result["errors"]
                ],
                "priority": classification["priority"],
                "severity": classification["severity"],
                "owner": classification["owner"],
                "cluster": classification["cluster"],
                "feedback_type": classification["feedback_type"],
                "status": "OPEN",
                "expected_behavior": f"状态应为 {expected}，不得返回 {observed}。",
                "source_report": report_path.name,
                "trace_id": result.get("trace_id"),
                "query_id": result.get("query_id"),
            }
        )
    return badcases


def import_to_feedback_board(badcases: list[dict[str, Any]]) -> tuple[int, int]:
    created = 0
    existing = 0
    with SessionLocal() as session:
        for item in badcases:
            row = session.get(UserFeedback, item["feedback_id"])
            if row is not None:
                existing += 1
                continue
            row = UserFeedback(
                feedback_id=item["feedback_id"],
                workspace_id="demo",
                conversation_id=f"golden_badcase_{item['case_id'].lower()}",
                operator_id=None,
                query_id=item["query_id"],
                user_query=item["query"],
                feedback_type=item["feedback_type"],
                severity=item["severity"],
                message=(
                    f"黄金集 {item['case_id']} 状态门禁不符合预期："
                    f"期望 {item['expected_status']}，实际 {item['observed_status']}。"
                ),
                expected_behavior=item["expected_behavior"],
                page_context={
                    "source": "olist_golden_evaluation",
                    "source_report": item["source_report"],
                    "golden_case_id": item["case_id"],
                    "split": item["split"],
                    "category": item["category"],
                    "cluster": item["cluster"],
                    "priority": item["priority"],
                    "owner": item["owner"],
                    "expected_status": item["expected_status"],
                    "observed_status": item["observed_status"],
                    "error_codes": item["error_codes"],
                    "already_in_golden_set": True,
                },
                snapshot_json={"trace_id": item["trace_id"]},
                status="OPEN",
                regression_candidate=False,
            )
            session.add(row)
            created += 1
        session.commit()
    return created, existing


def write_ledger(
    output_dir: Path,
    report: dict[str, Any],
    badcases: list[dict[str, Any]],
    created: int,
    existing: int,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "olist-golden-open-badcases.json"
    markdown_path = output_dir / "olist-golden-open-badcases.md"
    payload = {
        "ledger_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_evaluated_at": report["evaluated_at"],
        "total": len(badcases),
        "created_in_feedback_board": created,
        "already_existing": existing,
        "status_counts": dict(Counter(item["status"] for item in badcases)),
        "cluster_counts": dict(Counter(item["cluster"] for item in badcases)),
        "priority_counts": dict(Counter(item["priority"] for item in badcases)),
        "items": badcases,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Olist 黄金集 Bad Case 台账",
        "",
        f"- 总数：{len(badcases)}",
        f"- 本次写入反馈看板：{created}",
        f"- 已存在且跳过：{existing}",
        "- 当前状态：OPEN",
        "- 说明：这些问题已经属于黄金集，不重复进入黄金集候选流程。",
        "",
        "## 分类汇总",
        "",
        "| 根因簇 | 数量 |",
        "|---|---:|",
    ]
    for cluster, count in Counter(item["cluster"] for item in badcases).most_common():
        lines.append(f"| {cluster} | {count} |")
    lines.extend(
        [
            "",
            "## 明细",
            "",
            "| Case ID | 优先级 | Owner | 期望 | 实际 | 问题 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in badcases:
        query = item["query"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {item['case_id']} | {item['priority']} | {item['owner']} | "
            f"{item['expected_status']} | {item['observed_status']} | {query} |"
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    badcases = build_badcases(report, args.report)
    created, existing = import_to_feedback_board(badcases)
    json_path, markdown_path = write_ledger(
        args.output_dir, report, badcases, created, existing
    )
    print(
        f"Recorded {len(badcases)} bad cases: created={created}, existing={existing}; "
        f"ledgers={json_path},{markdown_path}"
    )


if __name__ == "__main__":
    main()
