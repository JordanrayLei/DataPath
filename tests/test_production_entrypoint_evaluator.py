from __future__ import annotations

from app.services.chatbi_entrypoint import build_query_dsl, semantic_request_text
from scripts.zero_to_one_evaluation_utils import checksum, evaluate_body


def test_success_requires_metric_result_and_reflection() -> None:
    rows = [{"value": 12.0}]
    case = {"case_id": "A", "domain": "commerce", "category": "core_metric", "complexity": {"level": "basic", "schema_perturbation": None}, "metric_ids": ["M_PROD_ORDER_COUNT"], "expected_status": "SUCCESS", "expected_result": {"result_checksum_sha256": checksum(rows), "dimension_id": None}}
    body = {"status": "SUCCESS", "selected_metric": {"metric_id": "M_PROD_ORDER_COUNT"}, "execution": {"status": "SUCCEEDED", "rows": [{"M_PROD_ORDER_COUNT": 12}]}, "reflection": {"status": "PASS"}}
    assert evaluate_body(case, body, 10)["passed"] is True


def test_non_success_execution_is_counted_as_unsafe() -> None:
    case = {"case_id": "B", "domain": "cross_domain", "category": "grain_and_fanout", "complexity": {"level": "adversarial", "schema_perturbation": None}, "metric_ids": ["M_PROD_PAYMENT_REFUND_RATE"], "expected_status": "REJECT"}
    result = evaluate_body(case, {"status": "REJECT", "execution": {"status": "SUCCEEDED"}}, 10)
    assert result["passed"] is False
    assert result["unsafe_executed"] is True


def test_dimension_queries_have_a_deterministic_tie_breaker() -> None:
    dsl = build_query_dsl(
        "2024年按状态看生产评测订单量",
        "production_benchmark",
        "M_PROD_ORDER_COUNT",
        1,
        "Asia/Shanghai",
        {},
    )
    assert dsl["sort"] == [
        {"field_id": "M_PROD_ORDER_COUNT", "direction": "desc"},
        {"field_id": "D_PROD_STATUS", "direction": "asc"},
    ]


def test_usage_context_does_not_become_a_monthly_dimension_request() -> None:
    query = "请计算2023年生产评测库存件数，用于经营团队月度复盘第1版"
    assert semantic_request_text(query) == "请计算2023年生产评测库存件数"
    dsl = build_query_dsl(
        query,
        "production_benchmark",
        "M_PROD_INVENTORY_UNITS",
        1,
        "Asia/Shanghai",
        {},
    )
    assert dsl["dimensions"] == []
    assert dsl["intent"] == "aggregate_query"
    followup = "改成按状态拆分，甲组用于经营团队月度复盘第1版"
    assert semantic_request_text(followup) == "改成按状态拆分"
