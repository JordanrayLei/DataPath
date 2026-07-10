from __future__ import annotations

import json

from scripts.evaluate_chatbi_entrypoint import PROJECT_ROOT, markdown_report, write_reports


def test_evaluation_report_files_are_written() -> None:
    report = {
        "generated_at": "2026-07-09T00:00:00+00:00",
        "target": "unit-test",
        "summary": {
            "status": "PASS",
            "passed": 2,
            "total": 2,
            "case_passed": 1,
            "case_total": 1,
            "gate_passed": 1,
            "gate_total": 1,
            "pass_rate": 1.0,
        },
        "cases": [
            {
                "name": "case_a",
                "passed": True,
                "errors": [],
                "query": "最近一年每月 GMV",
                "status": "SUCCESS",
                "selected_metric_id": "M_SALES_GMV",
                "dsl_intent": "trend_query",
                "chart_type": "line",
                "row_count": 12,
                "evidence_count": 3,
                "reflection_status": "PASS",
                "latency_ms": 10,
            }
        ],
        "gates": [
            {
                "name": "internal_service_token_guard",
                "passed": True,
                "detail": "rejected unauthenticated request",
            }
        ],
    }

    markdown = markdown_report(report)
    assert "ChatBI 产品入口测评报告" in markdown
    assert "总体状态：`PASS`" in markdown
    assert "case_a" in markdown

    output_dir = PROJECT_ROOT / ".tmp" / "evaluation-report-test"
    json_path, md_path, history_path = write_reports(report, output_dir, "eval")
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["status"] == "PASS"
    assert "internal_service_token_guard" in md_path.read_text(encoding="utf-8")
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["report_name"] == "eval"
    assert history["summary"]["status"] == "PASS"
