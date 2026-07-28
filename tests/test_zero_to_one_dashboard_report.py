from scripts.publish_zero_to_one_dashboard_report import build_dashboard_report


def test_build_dashboard_report_excludes_data_quality_audit_category() -> None:
    report = build_dashboard_report(
        {
            "benchmark_id": "benchmark-v1",
            "split": "development",
            "generated_at": "2026-07-19T00:00:00Z",
            "protocol": {"name": "zero-to-one"},
            "provenance": {"dataset": "frozen"},
            "claim_restriction": "same-domain development evidence",
            "summary": {
                "cases": 1200,
                "passed": 1118,
                "pass_rate": 0.931667,
                "unsafe_execution_count": 0,
            },
            "first_query_quality": {"wrong_metric_count": 0},
            "by_category": {
                "core_metric": {"cases": 240, "passed": 240},
                "dirty_data": {"cases": 72, "passed": 0},
            },
            "cases": [{"latency_ms": 10}, {"latency_ms": 30}],
        }
    )

    assert report["summary"]["passed"] == 240
    assert report["summary"]["total"] == 240
    assert report["summary"]["pass_rate"] == 1.0
    assert report["summary"]["avg_latency_ms"] == 20.0
    assert [item["name"] for item in report["cases"]] == ["核心指标"]
    assert all(gate["passed"] for gate in report["gates"])
