from __future__ import annotations

from app.schemas.chatbi import (
    MetricAdjudicationDecision,
    MetricAdjudicationValidateRequest,
    MetricCandidate,
    MetricMentionDecision,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
    PreprocessData,
)
from app.services.metric_adjudication import (
    issue_adjudication_token,
    validate_dify_metric_adjudication,
)


def test_adjudication_route_requires_backend_gate(client, service_headers) -> None:
    request_body = {
        "query": "订单量",
        "normalized_query": "订单量",
        "workspace_id": "demo",
        "biz_domain": "production_benchmark",
        "operator_id": "public_demo_user",
        "context": {},
        "preprocess": {
            "normalized_query": "订单量",
            "metric_mentions": ["订单量"],
            "dimension_mentions": [],
            "filter_mentions": [],
            "time_text": "",
            "time_start": "",
            "time_end": "",
            "comparison": "",
            "inherit_context": False,
        },
    }
    retrieval_response = client.post(
        "/api/chatbi/metrics/retrieve",
        headers=service_headers,
        json=request_body,
    )
    assert retrieval_response.status_code == 200
    retrieval = retrieval_response.json()
    assert retrieval["gate_status"] == "PASS"
    assert retrieval["adjudication_token"].startswith("mat.v1.")

    validation_response = client.post(
        "/api/chatbi/metrics/adjudicate/validate",
        headers=service_headers,
        json={
            **{key: request_body[key] for key in (
                "query", "normalized_query", "workspace_id", "biz_domain", "operator_id"
            )},
            "retrieval": retrieval,
            "adjudication_token": retrieval["adjudication_token"],
            "decisions": [{
                "mention_index": 0,
                "decision": "SUCCESS",
                "selected_metric_id": "M_PROD_ORDER_COUNT",
                "confidence": 0.99,
                "reason_code": "UNIQUE_MATCH",
                "clarification_question": "",
            }],
        },
    )
    assert validation_response.status_code == 200
    assert validation_response.json()["gate_status"] == "CLARIFY"
    assert validation_response.json()["reason_codes"] == ["ADJUDICATION_GATE_NOT_ELIGIBLE"]


def test_production_analyst_can_retrieve_production_metrics(client, service_headers) -> None:
    request_body = {
        "query": "成交单据数",
        "normalized_query": "成交单据数",
        "workspace_id": "demo",
        "biz_domain": "production_benchmark",
        "operator_id": "production_analyst",
        "context": {},
        "preprocess": {
            "normalized_query": "成交单据数",
            "metric_mentions": ["成交单据数"],
            "dimension_mentions": [],
            "filter_mentions": [],
            "time_text": "",
            "time_start": "",
            "time_end": "",
            "comparison": "",
            "inherit_context": False,
        },
    }
    response = client.post(
        "/api/chatbi/metrics/retrieve", headers=service_headers, json=request_body
    )
    assert response.status_code == 200


def test_operator_cannot_retrieve_outside_allowed_domain(client, service_headers) -> None:
    request_body = {
        "query": "成交单据数",
        "normalized_query": "成交单据数",
        "workspace_id": "demo",
        "biz_domain": "production_benchmark",
        "operator_id": "metric_admin",
        "context": {},
        "preprocess": {
            "normalized_query": "成交单据数",
            "metric_mentions": ["成交单据数"],
            "dimension_mentions": [],
            "filter_mentions": [],
            "time_text": "",
            "time_start": "",
            "time_end": "",
            "comparison": "",
            "inherit_context": False,
        },
    }
    response = client.post(
        "/api/chatbi/metrics/retrieve", headers=service_headers, json=request_body
    )
    assert response.status_code == 200
    assert response.json()["gate_status"] == "BLOCKED"
    assert response.json()["reason_codes"] == ["QUERY_CONTEXT_NOT_ALLOWED"]


def test_published_cross_fact_metric_is_retrievable_without_substitution(
    client, service_headers
) -> None:
    request_body = {
        "query": "请查看2024年扣除退款后的净收入，需要跨事实统一粒度",
        "normalized_query": "请查看2024年扣除退款后的净收入，需要跨事实统一粒度",
        "workspace_id": "demo",
        "biz_domain": "production_benchmark",
        "operator_id": "production_analyst",
        "context": {},
        "preprocess": {
            "normalized_query": "请查看2024年扣除退款后的净收入，需要跨事实统一粒度",
            "metric_mentions": ["扣除退款后的净收入"],
            "dimension_mentions": [],
            "filter_mentions": [],
            "time_text": "2024年",
            "time_start": "2024-01-01",
            "time_end": "2024-12-31",
            "comparison": "",
            "inherit_context": False,
        },
    }
    response = client.post(
        "/api/chatbi/metrics/retrieve", headers=service_headers, json=request_body
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gate_status"] == "PASS"
    assert body["reason_codes"] == ["EXACT_OR_ALIAS_MATCH"]
    assert body["mentions"][0]["selected_metric_id"] == (
        "M_PROD_REFUND_ADJUSTED_REVENUE"
    )


def retrieval_request() -> MetricRetrieveRequest:
    return MetricRetrieveRequest(
        query="去年实际到账多少钱",
        normalized_query="去年实际到账多少钱",
        workspace_id="demo",
        biz_domain="production_benchmark",
        operator_id="public_demo_user",
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


def uncertain_retrieval() -> MetricRetrieveResponse:
    candidates = [
        MetricCandidate(
            metric_id="M_PROD_PAYMENT_AMOUNT",
            metric_version=1,
            display_name="支付实收金额",
            metric_type="amount",
            unit="CNY",
            business_definition="支付事实中的净到账金额",
            probability=0.81,
            retrieval_sources=["embedding"],
            authorized=True,
        ),
        MetricCandidate(
            metric_id="M_PROD_ORDER_GROSS_AMOUNT",
            metric_version=1,
            display_name="订单原始金额",
            metric_type="amount",
            unit="CNY",
            business_definition="下单原始金额",
            probability=0.78,
            retrieval_sources=["embedding"],
            authorized=True,
        ),
    ]
    return MetricRetrieveResponse(
        request_id="req-adjudication",
        trace_id="trace-adjudication",
        gate_status="LLM_DISAMBIGUATE",
        mentions=[
            MetricMentionDecision(
                text="实际到账",
                selected_metric_id=candidates[0].metric_id,
                selected_metric_version=1,
                probability=0.81,
                candidates=candidates,
            )
        ],
        reason_codes=["HEURISTIC_CONFIDENCE_REQUIRES_DISAMBIGUATION"],
        clarification_message="",
    )


def validation_payload(
    *, confidence: float = 0.92, selected_metric_id: str = "M_PROD_PAYMENT_AMOUNT"
) -> MetricAdjudicationValidateRequest:
    request = retrieval_request()
    retrieval = uncertain_retrieval()
    token = issue_adjudication_token(request, retrieval)
    retrieval = retrieval.model_copy(update={"adjudication_token": token})
    return MetricAdjudicationValidateRequest(
        query=request.query,
        normalized_query=request.normalized_query,
        workspace_id=request.workspace_id,
        biz_domain=request.biz_domain,
        operator_id=request.operator_id,
        retrieval=retrieval,
        adjudication_token=token,
        decisions=[
            MetricAdjudicationDecision(
                mention_index=0,
                decision="SUCCESS",
                selected_metric_id=selected_metric_id,
                confidence=confidence,
                reason_code="UNIQUE_BUSINESS_EVENT_MATCH",
                clarification_question="",
            )
        ],
    )


def test_valid_dify_decision_can_pass_backend_gate(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.metric_adjudication._candidate_is_currently_published",
        lambda *args: True,
    )
    result = validate_dify_metric_adjudication(
        None, validation_payload()  # type: ignore[arg-type]
    )
    assert result.gate_status == "PASS"
    assert result.mentions[0].selected_metric_id == "M_PROD_PAYMENT_AMOUNT"
    assert result.adjudication_token == ""


def test_dify_cannot_select_metric_outside_signed_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.metric_adjudication._candidate_is_currently_published",
        lambda *args: True,
    )
    result = validate_dify_metric_adjudication(
        None, validation_payload(selected_metric_id="M_INVENTED")  # type: ignore[arg-type]
    )
    assert result.gate_status == "CLARIFY"
    assert result.reason_codes == ["ADJUDICATION_INVALID_OR_LOW_CONFIDENCE_SUCCESS"]


def test_low_confidence_dify_success_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.metric_adjudication._candidate_is_currently_published",
        lambda *args: True,
    )
    result = validate_dify_metric_adjudication(
        None, validation_payload(confidence=0.50)  # type: ignore[arg-type]
    )
    assert result.gate_status == "CLARIFY"


def test_calibrated_confidence_boundary_can_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.metric_adjudication._candidate_is_currently_published",
        lambda *args: True,
    )
    result = validate_dify_metric_adjudication(
        None, validation_payload(confidence=0.70)  # type: ignore[arg-type]
    )
    assert result.gate_status == "PASS"


def test_tampered_retrieval_candidate_fails_closed(monkeypatch) -> None:
    payload = validation_payload()
    payload.retrieval.mentions[0].candidates[0].metric_version = 99
    result = validate_dify_metric_adjudication(
        None, payload  # type: ignore[arg-type]
    )
    assert result.gate_status == "CLARIFY"
    assert result.reason_codes == ["ADJUDICATION_CANDIDATES_TAMPERED"]
