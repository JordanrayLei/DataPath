from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete, select

from app.db.models import ConversationContext, Metric, MetricVersion
from app.db.session import SessionLocal
from app.schemas.chatbi import QueryDsl
from app.schemas.chatbi import MetricRetrieveRequest
from app.services.access_policy import policy_for_operator
from app.services.join_planner import expression_model_ids
from app.services.query_compiler import _compile_aggregate_before_join
from app.services.dsl_validator import normalize_report_usage_time_grain, validate_dsl
from app.services.metric_retrieval import (
    build_dsl_generation_constraints,
    build_time_resolution_hint,
    retrieve_metrics,
)
from scripts.evaluate_dify_preheat import (
    apply_capability_profile,
    checkpoint_infrastructure_retry_ids,
    is_retryable_infrastructure_failure,
    load_capability_profile,
    select_failed_cases,
)
from scripts import evaluate_dify_preheat as dify_evaluator


ROOT = Path(__file__).resolve().parents[1]


def test_failed_case_selection_binds_baseline_and_categories(tmp_path: Path) -> None:
    cases = [
        {"case_id": "a", "category": "permission"},
        {"case_id": "b", "category": "performance"},
        {"case_id": "c", "category": "permission"},
    ]
    baseline_path = tmp_path / "development.json"
    baseline_path.write_text(
        json.dumps(
            {
                "split": "development",
                "provenance": {"golden_sha256": "sealed"},
                "cases": [
                    {"case_id": "a", "passed": False},
                    {"case_id": "b", "passed": False},
                    {"case_id": "c", "passed": True},
                ],
            }
        )
    )

    selected, selection = select_failed_cases(
        cases,
        baseline_path,
        ["permission"],
        {"development_sha256": "sealed"},
    )

    assert [case["case_id"] for case in selected] == ["a"]
    assert selection is not None
    assert selection["baseline_failed_case_count"] == 2
    assert selection["selected_case_count"] == 1
    assert len(selection["baseline_report_sha256"]) == 64
    assert len(selection["selected_case_ids_sha256"]) == 64
    assert len(selection["selection_sha256"]) == 64


def test_failed_case_selection_accepts_provenance_bound_checkpoint(tmp_path: Path) -> None:
    cases = [
        {"case_id": "a", "category": "cross_fact_join"},
        {"case_id": "b", "category": "cross_fact_join"},
    ]
    checkpoint_path = tmp_path / "development-checkpoint.json"
    checkpoint_path.write_text(
        json.dumps(
            {
                "split": "development",
                "golden_sha256": "sealed",
                "results": [
                    {"case_id": "a", "passed": False},
                    {"case_id": "b", "passed": True},
                ],
            }
        )
    )

    selected, selection = select_failed_cases(
        cases,
        checkpoint_path,
        ["cross_fact_join"],
        {"development_sha256": "sealed"},
    )

    assert [case["case_id"] for case in selected] == ["a"]
    assert selection is not None
    assert selection["selected_case_count"] == 1


def test_only_transient_workflow_failures_are_retryable() -> None:
    assert is_retryable_infrastructure_failure(
        {
            "body": {"status": "WORKFLOW_ERROR"},
            "stream_error": "PluginInvokeError: ChunkedEncodingError: Response ended prematurely",
        }
    )
    assert is_retryable_infrastructure_failure(
        {"body": {"status": "HTTP_ERROR", "http_status": 503}}
    )
    assert is_retryable_infrastructure_failure(
        {
            "body": {"status": "WORKFLOW_ERROR"},
            "stream_error": "Reached maximum retries for URL http://host.docker.internal:8000",
        }
    )
    assert is_retryable_infrastructure_failure(
        {
            "body": {"status": "WORKFLOW_ERROR"},
            "stream_error": "error: operation not permitted\n",
        }
    )
    assert not is_retryable_infrastructure_failure(
        {"body": {"status": "CLARIFY"}, "stream_error": ""}
    )
    assert not is_retryable_infrastructure_failure(
        {"body": {"status": "WORKFLOW_ERROR"}, "stream_error": "DSL output invalid"}
    )


def test_evaluator_retries_transient_failure_without_hiding_semantic_result(
    monkeypatch,
) -> None:
    outcomes = iter(
        [
            {
                "body": {"status": "WORKFLOW_ERROR"},
                "workflow_run_id": "failed-run",
                "stream_error": "ChunkedEncodingError: Response ended prematurely",
            },
            {
                "body": {"status": "REJECT"},
                "workflow_run_id": "successful-run",
                "stream_error": None,
            },
        ]
    )
    monkeypatch.setattr(dify_evaluator, "run_turn", lambda *args, **kwargs: next(outcomes))
    result = dify_evaluator.execute_case(
        None,
        "http://localhost/v1",
        "unused",
        {
            "case_id": "transient-retry",
            "query": "不支持的指标",
            "domain": "commerce",
            "category": "performance",
            "complexity": {"level": "simple", "schema_perturbation": None},
            "expected_status": "REJECT",
            "must_not_compile": True,
            "must_not_execute": True,
        },
        "analyst-token",
        "restricted-token",
        infrastructure_retries=1,
    )

    assert result["passed"]
    assert result["observed_status"] == "REJECT"
    assert result["infrastructure_retry_count"] == 1
    assert result["dify_workflow_run_ids"] == ["failed-run", "successful-run"]


def test_checkpoint_retry_requeues_only_dify_proven_transient_failures(
    monkeypatch,
) -> None:
    errors = {
        "transport-run": "Reached maximum retries for URL http://backend/context/save",
        "semantic-run": "DSL output invalid",
    }
    monkeypatch.setattr(
        dify_evaluator,
        "load_workflow_failure_detail",
        lambda client, base_url, headers, run_id: errors.get(run_id),
    )

    retry_ids, evidence = checkpoint_infrastructure_retry_ids(
        None,
        "http://localhost/v1",
        "unused",
        [
            {
                "case_id": "already-passed",
                "passed": True,
                "dify_workflow_run_id": "transport-run",
            },
            {
                "case_id": "transport-failure",
                "passed": False,
                "dify_workflow_run_ids": ["older-run", "transport-run"],
            },
            {
                "case_id": "semantic-failure",
                "passed": False,
                "dify_workflow_run_id": "semantic-run",
            },
        ],
    )

    assert retry_ids == {"transport-failure"}
    assert [item["case_id"] for item in evidence] == [
        "transport-failure",
        "semantic-failure",
    ]
    assert [item["retryable"] for item in evidence] == [True, False]


def test_cross_fact_capability_profile_preserves_sealed_input() -> None:
    data = ROOT / "data/evaluation/production/frontend_closure_v1"
    manifest = json.loads((data / "manifest.json").read_text())
    original = json.loads((data / "development.json").read_text())
    profile = load_capability_profile("cross_fact_v1", manifest)
    rewritten, counts = apply_capability_profile(original, profile)

    assert rewritten is not original
    assert counts == {
        "M_PROD_PAYMENT_REFUND_RATE": 60,
        "M_PROD_REFUND_ADJUSTED_REVENUE": 60,
    }
    assert sum(case["expected_status"] == "REJECT" for case in original) == 144
    overlaid = [case for case in rewritten if case.get("expectation_overlay")]
    assert len(overlaid) == 120
    assert all(case["expected_status"] == "SUCCESS" for case in overlaid)
    assert all(not case["must_not_compile"] and not case["must_not_execute"] for case in overlaid)


def test_cross_fact_capability_profile_does_not_open_unsupported_shapes() -> None:
    data = ROOT / "data/evaluation/production/frontend_closure_v1"
    manifest = json.loads((data / "manifest.json").read_text())
    profile = load_capability_profile("cross_fact_v1", manifest)
    original = json.loads((data / "development.json").read_text())
    unsupported = {
        "case_id": "unsupported-dimension",
        "query": "按月查看2024年扣除退款后的净收入",
        "expected_status": "REJECT",
        "category": "grain_and_fanout",
        "sql_skeleton_id": "aggregate_before_join_multi_fact",
        "metric_ids": ["M_PROD_REFUND_ADJUSTED_REVENUE"],
        "dimension_ids": ["D_MONTH"],
        "filters": [],
    }
    rewritten, counts = apply_capability_profile([*original, unsupported], profile)
    assert sum(counts.values()) == 120
    assert rewritten[-1]["expected_status"] == "REJECT"


def test_cross_fact_preheat_package_is_definition_only() -> None:
    package = json.loads(
        (ROOT / "data/semantic_bootstrap/production_cross_fact_preheat_v1.json").read_text()
    )
    assert package["generation_mode"] == "canonical-definition-only"
    assert set(package["metrics"]) == {
        "M_PROD_REFUND_ADJUSTED_REVENUE",
        "M_PROD_PAYMENT_REFUND_RATE",
    }
    assert "no evaluation questions" in package["source_restriction"].casefold()


def test_subtract_expression_discovers_both_fact_models() -> None:
    expression = {
        "op": "subtract",
        "left": {"op": "sum", "field": "net_amount"},
        "right": {
            "op": "sum",
            "field": "net_amount",
            "source_model_id": "SM_PROD_REFUNDS",
        },
    }
    assert expression_model_ids(expression, "SM_PROD_ORDER_ITEMS") == {
        "SM_PROD_ORDER_ITEMS",
        "SM_PROD_REFUNDS",
    }


def test_cross_fact_sql_uses_aggregate_before_join() -> None:
    with SessionLocal() as session:
        version = session.scalar(
            select(MetricVersion)
            .where(MetricVersion.metric_id == "M_PROD_PAYMENT_REFUND_RATE")
            .order_by(MetricVersion.version.desc())
        )
        assert version is not None
        policy = policy_for_operator("production_analyst")
        assert policy is not None
        dsl = QueryDsl.model_validate(
            {
                "dsl_version": "2.0",
                "query_mode": "multi_fact",
                "intent": "aggregate_query",
                "metrics": [
                    {
                        "metric_id": version.metric_id,
                        "metric_version": version.version,
                        "aggregation": "default",
                    }
                ],
                "dimensions": [],
                "filters": [],
                "time_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31",
                    "timezone": "Asia/Shanghai",
                },
                "sort": [],
                "limit": 5000,
            }
        )
        sql, _, tables, _, models = _compile_aggregate_before_join(
            session, dsl, version, policy
        )
    assert "CROSS JOIN" in sql
    assert "production_benchmark.fct_payments" in sql
    assert "production_benchmark.fct_refunds" in sql
    assert sql.index("sum(net_amount)") < sql.index("CROSS JOIN")
    assert set(tables) == {
        "production_benchmark.fct_payments",
        "production_benchmark.fct_refunds",
    }
    assert set(models) == {"SM_PROD_PAYMENTS", "SM_PROD_REFUNDS"}


def test_cross_fact_dimension_fails_closed() -> None:
    with SessionLocal() as session:
        version = session.scalar(
            select(MetricVersion)
            .where(MetricVersion.metric_id == "M_PROD_PAYMENT_REFUND_RATE")
            .order_by(MetricVersion.version.desc())
        )
        policy = policy_for_operator("production_analyst")
        dsl = QueryDsl.model_validate(
            {
                "dsl_version": "2.0",
                "query_mode": "multi_fact",
                "intent": "trend_query",
                "metrics": [{"metric_id": version.metric_id, "metric_version": version.version, "aggregation": "default"}],
                "dimensions": [{"dimension_id": "D_MONTH"}],
                "filters": [],
                "time_range": {"start": "2024-01-01", "end": "2024-12-31", "timezone": "Asia/Shanghai"},
                "sort": [{"field_id": "D_MONTH", "direction": "asc"}],
                "limit": 100,
            }
        )
        try:
            _compile_aggregate_before_join(session, dsl, version, policy)
        except ValueError as error:
            assert "shared-grain contract" in str(error)
        else:
            raise AssertionError("cross-fact dimension must fail closed")


def _time_request(
    query: str,
    *,
    inherit_context: bool = False,
    last_query_context: dict | None = None,
) -> MetricRetrieveRequest:
    return MetricRetrieveRequest.model_validate(
        {
            "query": query,
            "normalized_query": query,
            "workspace_id": "demo",
            "biz_domain": "production_benchmark",
            "operator_id": "production_analyst",
            "context": {"last_query_context": last_query_context or {}},
            "preprocess": {
                "normalized_query": query,
                "metric_mentions": ["订单量"],
                "dimension_mentions": [],
                "filter_mentions": [],
                "time_text": "",
                "time_start": "",
                "time_end": "",
                "comparison": "",
                "inherit_context": inherit_context,
            },
        }
    )


def test_monthly_report_usage_is_not_a_month_dimension() -> None:
    assert not build_time_resolution_hint(
        _time_request("查看订单量，用于月度复盘")
    )["detected_time_need"]["looks_monthly"]
    assert not build_time_resolution_hint(
        _time_request("查看订单量，用于履约团队月度复盘第1版")
    )["detected_time_need"]["looks_monthly"]


def test_validator_removes_only_llm_invented_report_usage_month_grain() -> None:
    raw = {
        "intent": "aggregate_query",
        "dimensions": [{"dimension_id": "D_MONTH"}],
        "sort": [{"field_id": "D_MONTH", "direction": "asc"}],
    }
    normalized = normalize_report_usage_time_grain(
        raw, "查看退款后净收入，用于履约团队月度复盘第1版"
    )
    explicit = normalize_report_usage_time_grain(
        raw, "按月查看退款后净收入，用于履约团队月度复盘"
    )

    assert normalized["dimensions"] == []
    assert normalized["sort"] == []
    assert explicit == raw


def test_production_followup_inherits_time_without_fixed_demo_window() -> None:
    request = _time_request(
        "再按币种展示",
        inherit_context=True,
        last_query_context={
            "biz_domain": "production_benchmark",
            "metrics": [{"metric_id": "M_PROD_PAYMENT_AMOUNT"}],
            "time_range": {
                "start": "2024-01-01",
                "end": "2024-12-31",
                "timezone": "Asia/Shanghai",
            },
        },
    )
    hint = build_time_resolution_hint(request)
    constraints = build_dsl_generation_constraints(request)

    assert hint["inherited_time_range"] == {
        "start": "2024-01-01",
        "end": "2024-12-31",
        "timezone": "Asia/Shanghai",
    }
    assert "warehouse_data_window" not in hint
    assert "2017-10-01" not in json.dumps([hint, constraints])


def test_dimension_only_followup_uses_unique_validated_metric_context() -> None:
    request = _time_request(
        "再按币种展示",
        inherit_context=True,
        last_query_context={
            "biz_domain": "production_benchmark",
            "metrics": [{"metric_id": "M_PROD_PAYMENT_AMOUNT"}],
            "time_range": {
                "start": "2024-01-01",
                "end": "2024-12-31",
                "timezone": "Asia/Shanghai",
            },
        },
    )
    with SessionLocal() as session:
        response = retrieve_metrics(session, request, "test-request", "test-trace")

    assert response.gate_status == "PASS"
    assert response.reason_codes == ["VALIDATED_CONVERSATION_CONTEXT"]
    assert response.mentions[0].selected_metric_id == "M_PROD_PAYMENT_AMOUNT"
    assert response.mentions[0].probability == 1.0
    assert response.mentions[0].candidates[0].retrieval_sources == [
        "validated_conversation_context"
    ]


def test_full_governed_alias_overrides_shortened_llm_metric_mention() -> None:
    query = "请查看2024年扣除退款后的净收入，需要跨事实统一粒度"
    request = MetricRetrieveRequest.model_validate(
        {
            "query": query,
            "normalized_query": query,
            "workspace_id": "demo",
            "biz_domain": "production_benchmark",
            "operator_id": "production_analyst",
            "context": {},
            "preprocess": {
                "normalized_query": query,
                # Simulate the lossy extraction observed in the Dify failure.
                "metric_mentions": ["净收入"],
                "dimension_mentions": [],
                "filter_mentions": [],
                "time_text": "2024年",
                "time_start": "2024-01-01",
                "time_end": "2024-12-31",
                "comparison": "",
                "inherit_context": False,
            },
        }
    )
    with SessionLocal() as session:
        # The shared fixture intentionally leaves cross-fact metrics staged.
        # Temporarily model the public-API publication used by this capability
        # profile, then roll the transaction back after the assertion.
        metric = session.get(Metric, "M_PROD_REFUND_ADJUSTED_REVENUE")
        assert metric is not None
        metric.status = "PUBLISHED"
        session.flush()
        response = retrieve_metrics(session, request, "test-request", "test-trace")
        session.rollback()

    assert response.gate_status == "PASS"
    assert response.mentions[0].selected_metric_id == "M_PROD_REFUND_ADJUSTED_REVENUE"
    assert response.mentions[0].candidates[0].probability >= 0.99


def test_dsl_validator_normalizes_llm_query_mode_from_safe_join_plan() -> None:
    with SessionLocal() as session:
        version = session.scalar(
            select(MetricVersion).where(
                MetricVersion.metric_id == "M_PROD_SHIPMENT_COUNT",
                MetricVersion.status == "PUBLISHED",
            )
        )
        assert version is not None
        response = validate_dsl(
            session,
            {
                "dsl_version": "2.0",
                # Simulate a plausible LLM mistake.  The deterministic planner
                # must derive multi_entity from D_PROD_WAREHOUSE instead.
                "query_mode": "single_model",
                "intent": "aggregate_query",
                "metrics": [
                    {
                        "metric_id": version.metric_id,
                        "metric_version": version.version,
                        "aggregation": "default",
                    }
                ],
                "dimensions": [{"dimension_id": "D_PROD_WAREHOUSE"}],
                "filters": [],
                "time_range": {
                    "start": "2023-01-01",
                    "end": "2023-12-31",
                    "timezone": "Asia/Shanghai",
                },
                "sort": [],
                "limit": 100,
            },
            {"allowed_domains": ["production_benchmark"]},
            "test-request",
            "test-trace",
        )

    assert response.status == "VALID"
    assert response.normalized_dsl is not None
    assert response.normalized_dsl["query_mode"] == "multi_entity"
    assert response.normalized_dsl["sort"] == [
        {"field_id": "M_PROD_SHIPMENT_COUNT", "direction": "desc"},
        {"field_id": "D_PROD_WAREHOUSE", "direction": "asc"}
    ]
    assert response.normalized_dsl["limit"] == 100


def test_dify_can_save_validated_multiturn_context(client, service_headers) -> None:
    conversation_id = "cross_fact_context_save_test"
    response = client.post(
        "/api/chatbi/context/save",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "conversation_id": conversation_id,
            "operator_id": "production_analyst",
            "biz_domain": "production_benchmark",
            "dsl": {
                "dsl_version": "2.0",
                "query_mode": "single_model",
                "intent": "aggregate_query",
                "metrics": [
                    {
                        "metric_id": "M_PROD_ORDER_COUNT",
                        "metric_version": 1,
                        "aggregation": "default",
                    }
                ],
                "dimensions": [],
                "filters": [],
                "time_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31",
                    "timezone": "Asia/Shanghai",
                },
                "sort": [],
                "limit": 100,
            },
        },
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as session:
        context = session.scalar(
            select(ConversationContext).where(
                ConversationContext.conversation_id == conversation_id
            )
        )
        assert context is not None
        assert context.last_query_context["metrics"][0]["metric_id"] == "M_PROD_ORDER_COUNT"
        session.execute(
            delete(ConversationContext).where(
                ConversationContext.conversation_id == conversation_id
            )
        )
        session.commit()
    assert build_time_resolution_hint(
        _time_request("按月查看订单量趋势")
    )["detected_time_need"]["looks_monthly"]
