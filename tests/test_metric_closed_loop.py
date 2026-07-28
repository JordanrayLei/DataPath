from types import SimpleNamespace

import pytest

from app.schemas.chatbi import GoldenQuestionCreateFromFeedbackRequest, MetricClosureValidationRequest
from app.services.metric_closed_loop import lexical_decision
from app.services.metric_retrieval import MetricRecord


def record(
    metric_id: str,
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    positive_examples: tuple[str, ...] = (),
    negative_examples: tuple[str, ...] = (),
) -> MetricRecord:
    return MetricRecord(
        metric=SimpleNamespace(
            id=metric_id,
            name=name,
            description=f"{name}的治理口径",
            metric_type="amount",
            unit="CNY",
        ),
        version=SimpleNamespace(version=2),
        aliases=aliases,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
    )


def test_operator_positive_example_changes_badcase_candidate() -> None:
    query = "查看成交净额"
    before = [
        record("M_ORDER_AMOUNT", "订单金额", aliases=("成交额",)),
        record("M_NET_REVENUE", "净收入"),
    ]
    after = [
        before[0],
        record(
            "M_NET_REVENUE",
            "净收入",
            positive_examples=(query,),
        ),
    ]

    baseline = lexical_decision(query, before)
    candidate = lexical_decision(query, after)

    assert baseline["selected_metric_id"] != "M_NET_REVENUE"
    assert candidate["selected_metric_id"] == "M_NET_REVENUE"
    assert candidate["gate_status"] in {"PASS", "LLM_DISAMBIGUATE"}
    assert "positive_example" in candidate["sources"]


def test_success_closure_requires_operator_confirmed_metric() -> None:
    with pytest.raises(ValueError, match="expected metric"):
        MetricClosureValidationRequest(
            feedback_id="fb_1",
            expected_status="SUCCESS",
        )


def test_non_success_closure_may_deliberately_have_no_metric() -> None:
    payload = MetricClosureValidationRequest(
        feedback_id="fb_1",
        expected_status="CLARIFY",
        expected_metric_id=None,
    )
    assert payload.expected_metric_id is None


def test_success_golden_contract_cannot_inherit_an_unconfirmed_metric() -> None:
    with pytest.raises(ValueError, match="operator-confirmed metric"):
        GoldenQuestionCreateFromFeedbackRequest(expected_status="SUCCESS")
