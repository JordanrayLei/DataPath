from __future__ import annotations

from app.schemas.chatbi import (
    MetricCandidate,
    MetricMentionDecision,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
    PreprocessData,
)
from app.services.metric_judge import (
    HttpMetricJudgeProvider,
    MetricJudgeOutput,
    MetricJudgeResult,
    adjudicate_metric_candidates,
    get_metric_judge_provider,
)
from app.config import get_settings


class FakeJudge:
    name = "fake_ai_judge"

    def __init__(self, output: MetricJudgeOutput) -> None:
        self.output = output
        self.calls = 0

    def judge(self, payload: dict) -> MetricJudgeResult:
        self.calls += 1
        return MetricJudgeResult(
            output=self.output,
            provider=self.name,
            model="fake-model-v1",
        )


def request() -> MetricRetrieveRequest:
    return MetricRetrieveRequest(
        query="去年实际到账多少钱",
        normalized_query="去年实际到账多少钱",
        workspace_id="demo",
        biz_domain="production_benchmark",
        operator_id="analyst",
        context={},
        preprocess=PreprocessData(
            normalized_query="去年实际到账多少钱",
            metric_mentions=["实际到账"],
            dimension_mentions=[],
            filter_mentions=[],
            time_text="去年",
            time_start="2024-01-01",
            time_end="2024-12-31",
            comparison="",
            inherit_context=False,
        ),
    )


def retrieval(gate_status: str = "LLM_DISAMBIGUATE") -> MetricRetrieveResponse:
    candidates = [
        MetricCandidate(
            metric_id="M_PROD_PAYMENT_AMOUNT",
            metric_version=2,
            display_name="支付实收金额",
            metric_type="amount",
            unit="CNY",
            business_definition="支付事实中的净到账金额",
            probability=0.81,
            retrieval_sources=["embedding", "bm25"],
            authorized=True,
        ),
        MetricCandidate(
            metric_id="M_PROD_ORDER_GROSS_AMOUNT",
            metric_version=2,
            display_name="订单原始金额",
            metric_type="amount",
            unit="CNY",
            business_definition="下单时的原始金额，不代表实际到账",
            probability=0.78,
            retrieval_sources=["embedding", "bm25"],
            authorized=True,
        ),
    ]
    return MetricRetrieveResponse(
        request_id="req",
        trace_id="trace",
        gate_status=gate_status,
        mentions=[
            MetricMentionDecision(
                text="实际到账",
                selected_metric_id=candidates[0].metric_id,
                selected_metric_version=candidates[0].metric_version,
                probability=candidates[0].probability,
                candidates=candidates,
            )
        ],
        reason_codes=["HEURISTIC_CONFIDENCE_REQUIRES_DISAMBIGUATION"],
        clarification_message="",
    )


def patch_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.metric_judge.build_metric_judge_payload",
        lambda session, request, mention: {"candidates": [
            {"metric_id": item.metric_id} for item in mention.candidates
        ]},
    )


def test_ai_judge_can_promote_unique_candidate(monkeypatch) -> None:
    patch_payload(monkeypatch)
    judge = FakeJudge(
        MetricJudgeOutput(
            decision="SUCCESS",
            selected_metric_id="M_PROD_PAYMENT_AMOUNT",
            confidence=0.92,
            reason_code="UNIQUE_BUSINESS_EVENT_MATCH",
            matched_concepts=["到账"],
        )
    )
    result, records = adjudicate_metric_candidates(
        None, request(), retrieval(), provider=judge  # type: ignore[arg-type]
    )
    assert result.gate_status == "PASS"
    assert result.mentions[0].selected_metric_id == "M_PROD_PAYMENT_AMOUNT"
    assert result.mentions[0].probability == 0.92
    assert records[0].provider == "fake_ai_judge"


def test_ai_judge_cannot_select_outside_candidate_set(monkeypatch) -> None:
    patch_payload(monkeypatch)
    judge = FakeJudge(
        MetricJudgeOutput(
            decision="SUCCESS",
            selected_metric_id="M_INVENTED",
            confidence=0.99,
            reason_code="UNIQUE_MATCH",
        )
    )
    result, records = adjudicate_metric_candidates(
        None, request(), retrieval(), provider=judge  # type: ignore[arg-type]
    )
    assert result.gate_status == "CLARIFY"
    assert result.mentions[0].selected_metric_id == ""
    assert records[0].fallback is True
    assert records[0].error_code == "JUDGE_INVALID_OR_LOW_CONFIDENCE_SUCCESS"


def test_low_confidence_success_fails_closed(monkeypatch) -> None:
    patch_payload(monkeypatch)
    judge = FakeJudge(
        MetricJudgeOutput(
            decision="SUCCESS",
            selected_metric_id="M_PROD_PAYMENT_AMOUNT",
            confidence=0.60,
            reason_code="WEAK_MATCH",
        )
    )
    result, _ = adjudicate_metric_candidates(
        None, request(), retrieval(), provider=judge  # type: ignore[arg-type]
    )
    assert result.gate_status == "CLARIFY"
    assert result.mentions[0].selected_metric_version is None


def test_deterministic_pass_skips_ai_judge(monkeypatch) -> None:
    patch_payload(monkeypatch)
    judge = FakeJudge(
        MetricJudgeOutput(
            decision="CLARIFY",
            confidence=0.0,
            reason_code="AMBIGUOUS",
        )
    )
    result, records = adjudicate_metric_candidates(
        None, request(), retrieval("PASS"), provider=judge  # type: ignore[arg-type]
    )
    assert result.gate_status == "PASS"
    assert records == []
    assert judge.calls == 0


def test_deepseek_provider_uses_native_openai_compatible_endpoint(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "metric_judge_provider", "deepseek")
    monkeypatch.setattr(settings, "deepseek_base_url", "https://api.deepseek.com")
    monkeypatch.setattr(settings, "deepseek_api_key", "configured-for-test")
    monkeypatch.setattr(settings, "deepseek_model", "deepseek-v4-flash")
    provider = get_metric_judge_provider()
    assert isinstance(provider, HttpMetricJudgeProvider)
    assert provider.url == "https://api.deepseek.com/chat/completions"
    assert provider.model == "deepseek-v4-flash"
    assert provider.name == "deepseek_structured_metric_judge"
