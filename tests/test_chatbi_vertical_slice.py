from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import EvidenceRecord, QueryRun, ReflectionValidation, ResultProfile
from app.config import get_settings
from app.db.session import SessionLocal
from tests.conftest import preprocess


def test_context_requires_service_auth(client: TestClient) -> None:
    response = client.post(
        "/api/chatbi/context/load",
        json={
            "workspace_id": "demo",
            "conversation_id": "conv_test",
            "identity_token": get_settings().demo_identity_token,
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_SERVICE_TOKEN"


def test_context_loads_demo_policy(client: TestClient, service_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/chatbi/context/load",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "conversation_id": "conv_test",
            "identity_token": get_settings().demo_identity_token,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["operator_id"] == "public_demo_user"
    assert body["allowed_domains"] == ["sales", "advertising"]
    assert body["row_policy_token"].startswith("rpt.v1.")
    assert body["request_id"] == "req_test_001"


def test_metric_ambiguity_and_exact_match(
    client: TestClient, service_headers: dict[str, str]
) -> None:
    base = {
        "workspace_id": "demo",
        "biz_domain": "sales",
        "operator_id": "public_demo_user",
        "context": {},
    }
    ambiguous = client.post(
        "/api/chatbi/metrics/retrieve",
        headers=service_headers,
        json={
            **base,
            "query": "看看毛利",
            "normalized_query": "看看毛利",
            "preprocess": preprocess(["毛利"]),
        },
    )
    assert ambiguous.status_code == 200
    ambiguous_body = ambiguous.json()
    assert ambiguous_body["gate_status"] == "CLARIFY"
    assert {item["metric_id"] for item in ambiguous_body["mentions"][0]["candidates"][:2]} == {
        "M_SALES_GROSS_PROFIT",
        "M_SALES_GROSS_MARGIN_RATE",
    }

    exact = client.post(
        "/api/chatbi/metrics/retrieve",
        headers=service_headers,
        json={
            **base,
            "query": "查询毛利率",
            "normalized_query": "查询毛利率",
            "preprocess": preprocess(["毛利率"]),
        },
    )
    assert exact.status_code == 200
    exact_body = exact.json()
    assert exact_body["gate_status"] == "PASS"
    assert exact_body["mentions"][0]["selected_metric_id"] == "M_SALES_GROSS_MARGIN_RATE"
    time_hint = exact_body["time_resolution"]
    assert time_hint["warehouse_data_window"]["latest_data_date"] == "2026-06-30"
    assert time_hint["relative_time_policy"]["recent_year_monthly_default"]["start"] == "2025-07-01"
    assert time_hint["relative_time_policy"]["recent_year_monthly_default"]["end"] == "2026-06-30"
    assert any("D_MONTH" in item for item in exact_body["dsl_generation_constraints"])


def sales_gmv_dsl() -> dict:
    return {
        "dsl_version": "1.0",
        "intent": "trend_query",
        "metrics": [
            {
                "metric_id": "M_SALES_GMV",
                "metric_version": 1,
                "aggregation": "default",
            }
        ],
        "dimensions": [{"dimension_id": "D_MONTH"}],
        "filters": [
            {
                "field_id": "D_SALES_CHANNEL",
                "operator": "eq",
                "values": ["app"],
            }
        ],
        "time_range": {
            "start": "2025-07-01",
            "end": "2026-06-30",
            "timezone": "Asia/Shanghai",
        },
        "sort": [{"field_id": "D_MONTH", "direction": "asc"}],
        "limit": 100,
    }


def test_validator_rejects_unknown_metric(
    client: TestClient, service_headers: dict[str, str]
) -> None:
    dsl = sales_gmv_dsl()
    dsl["metrics"][0]["metric_id"] = "M_UNKNOWN_METRIC"
    response = client.post(
        "/api/chatbi/dsl/validate",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "row_policy_context": {"allowed_domains": ["sales", "advertising"]},
            "dsl": dsl,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INVALID"
    assert response.json()["issues"][0]["code"] == "METRIC_VERSION_NOT_PUBLISHED"


def test_compile_and_execute_uses_server_side_sql(
    client: TestClient, service_headers: dict[str, str]
) -> None:
    dsl = sales_gmv_dsl()
    policy = {"allowed_domains": ["sales", "advertising"]}
    validation = client.post(
        "/api/chatbi/dsl/validate",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "row_policy_context": policy,
            "dsl": dsl,
        },
    )
    assert validation.status_code == 200
    assert validation.json()["status"] == "VALID"

    compile_response = client.post(
        "/api/chatbi/query/compile",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "dsl": validation.json()["normalized_dsl"],
            "permission_context": policy,
        },
    )
    assert compile_response.status_code == 200, compile_response.text
    compiled = compile_response.json()
    assert compiled["status"] == "READY"
    assert compiled["execution_token"].startswith("v1.")
    serialized_compiled = json.dumps(compiled).upper()
    assert "SELECT " not in serialized_compiled
    assert "FROM DATA_WAREHOUSE" not in serialized_compiled
    assert "compiled_query" not in compiled

    with SessionLocal() as session:
        run = session.scalar(select(QueryRun).where(QueryRun.query_id == compiled["query_id"]))
        assert run is not None
        assert "DROP" not in run.sql_text.upper()
        assert "data_warehouse.dwd_sales_order_item" in run.sql_text

    execute_headers = {
        **service_headers,
        "Idempotency-Key": compiled["query_id"],
    }
    missing_token = client.post(
        "/api/chatbi/query/execute",
        headers=execute_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "query_id": compiled["query_id"],
        },
    )
    assert missing_token.status_code == 409
    assert "execution token is required" in missing_token.text

    execute_response = client.post(
        "/api/chatbi/query/execute",
        headers=execute_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "query_id": compiled["query_id"],
            "execution_token": compiled["execution_token"],
            "compiled_query": {"sql": "DROP TABLE data_warehouse.dwd_sales_order_item"},
        },
    )
    assert execute_response.status_code == 200, execute_response.text
    result = execute_response.json()
    assert result["status"] == "SUCCEEDED"
    assert result["row_count"] == 12
    assert result["rows"][0]["D_MONTH"].startswith("2025-")
    assert "M_SALES_GMV" in result["rows"][0]
    assert result["cached"] is False

    repeated = client.post(
        "/api/chatbi/query/execute",
        headers=execute_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "query_id": compiled["query_id"],
            "compiled_query": {"sql": "SELECT 999999"},
        },
    )
    assert repeated.status_code == 200
    assert repeated.json()["cached"] is True
    assert repeated.json()["rows"] == result["rows"]

    tampered_result = {**result, "rows": [dict(row) for row in result["rows"]]}
    tampered_result["rows"][0]["M_SALES_GMV"] = 999_999_999
    profile_response = client.post(
        "/api/chatbi/result/profile",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "query_id": compiled["query_id"],
            "execution_result": tampered_result,
            "dsl": validation.json()["normalized_dsl"],
        },
    )
    assert profile_response.status_code == 200, profile_response.text
    profile = profile_response.json()
    assert profile["profile_version"] == "1.0"
    assert profile["chart_spec"]["type"] == "line"
    assert profile["trend_summary"][0]["point_count"] == 12
    assert profile["headline_metrics"][0]["value"] != 999_999_999
    assert len(profile["evidence"]) >= 2
    assert len({item["evidence_id"] for item in profile["evidence"]}) == len(profile["evidence"])
    assert all(item["query_id"] == compiled["query_id"] for item in profile["evidence"])
    assert all(item["calculation"] and item["row_refs"] for item in profile["evidence"])

    repeated_profile = client.post(
        "/api/chatbi/result/profile",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "query_id": compiled["query_id"],
            "execution_result": result,
            "dsl": validation.json()["normalized_dsl"],
        },
    )
    assert repeated_profile.status_code == 200
    assert repeated_profile.json()["profile_id"] == profile["profile_id"]
    assert repeated_profile.json()["evidence"] == profile["evidence"]

    with SessionLocal() as session:
        stored_profile = session.scalar(
            select(ResultProfile).where(ResultProfile.query_id == compiled["query_id"])
        )
        stored_evidence = session.scalars(
            select(EvidenceRecord).where(EvidenceRecord.query_id == compiled["query_id"])
        ).all()
        assert stored_profile is not None
        assert len(stored_evidence) == len(profile["evidence"])

    first_evidence = profile["evidence"][0]
    reflection_base = {
        "workspace_id": "demo",
        "query_id": compiled["query_id"],
        "dsl": validation.json()["normalized_dsl"],
        "profile": profile,
    }
    generated = client.post(
        "/api/chatbi/interpretation/generate",
        headers=service_headers,
        json=reflection_base,
    )
    assert generated.status_code == 200, generated.text
    generated_interpretation = generated.json()["interpretation"]
    assert generated_interpretation["findings"]
    assert generated_interpretation["findings"][0]["text"] == first_evidence["statement"]
    generated_pass = client.post(
        "/api/chatbi/reflection/validate",
        headers=service_headers,
        json={**reflection_base, "interpretation": generated_interpretation},
    )
    assert generated_pass.status_code == 200, generated_pass.text
    assert generated_pass.json()["status"] == "PASS"

    valid_interpretation = {
        "title": "GMV 趋势分析",
        "findings": [
            {
                "text": first_evidence["statement"],
                "evidence_ids": [first_evidence["evidence_id"]],
            }
        ],
        "caveats": profile["caveats"],
        "next_actions": ["可继续按地区下钻"],
    }
    passed = client.post(
        "/api/chatbi/reflection/validate",
        headers=service_headers,
        json={**reflection_base, "interpretation": valid_interpretation},
    )
    assert passed.status_code == 200, passed.text
    assert passed.json()["status"] == "PASS"
    assert passed.json()["issues"] == []

    repeated_pass = client.post(
        "/api/chatbi/reflection/validate",
        headers=service_headers,
        json={**reflection_base, "interpretation": valid_interpretation},
    )
    assert repeated_pass.status_code == 200
    assert repeated_pass.json()["status"] == "PASS"

    causal_interpretation = {
        **valid_interpretation,
        "findings": [
            {
                "text": f'{first_evidence["statement"]} 该变化导致整体业务增长。',
                "evidence_ids": [first_evidence["evidence_id"]],
            }
        ],
    }
    revised = client.post(
        "/api/chatbi/reflection/validate",
        headers=service_headers,
        json={**reflection_base, "interpretation": causal_interpretation},
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["status"] == "REVISE"
    assert "UNSUPPORTED_CAUSAL_CLAIM" in {
        item["code"] for item in revised.json()["issues"]
    }

    numeric_interpretation = {
        **valid_interpretation,
        "findings": [
            {
                "text": "GMV 为 999999999 CNY。",
                "evidence_ids": [first_evidence["evidence_id"]],
            }
        ],
    }
    blocked = client.post(
        "/api/chatbi/reflection/validate",
        headers=service_headers,
        json={**reflection_base, "interpretation": numeric_interpretation},
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["status"] == "BLOCK"
    assert "NUMERIC_MISMATCH" in {item["code"] for item in blocked.json()["issues"]}

    unknown_interpretation = {
        **valid_interpretation,
        "findings": [{"text": "GMV 有变化。", "evidence_ids": ["ev_unknown"]}],
    }
    unknown = client.post(
        "/api/chatbi/reflection/validate",
        headers=service_headers,
        json={**reflection_base, "interpretation": unknown_interpretation},
    )
    assert unknown.status_code == 200, unknown.text
    assert unknown.json()["status"] == "BLOCK"
    assert unknown.json()["issues"][0]["code"] == "UNKNOWN_EVIDENCE_ID"

    with SessionLocal() as session:
        validations = session.scalars(
            select(ReflectionValidation).where(
                ReflectionValidation.query_id == compiled["query_id"]
            )
        ).all()
        assert len(validations) == 5


def test_profile_dimension_contributions(
    client: TestClient, service_headers: dict[str, str]
) -> None:
    dsl = {
        "dsl_version": "1.0",
        "intent": "ranking_query",
        "metrics": [
            {
                "metric_id": "M_SALES_GMV",
                "metric_version": 1,
                "aggregation": "default",
            }
        ],
        "dimensions": [{"dimension_id": "D_REGION"}],
        "filters": [],
        "time_range": {
            "start": "2025-07-01",
            "end": "2026-06-30",
            "timezone": "Asia/Shanghai",
        },
        "sort": [{"field_id": "M_SALES_GMV", "direction": "desc"}],
        "limit": 100,
    }
    policy = {"allowed_domains": ["sales", "advertising"]}
    validation = client.post(
        "/api/chatbi/dsl/validate",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "row_policy_context": policy,
            "dsl": dsl,
        },
    )
    assert validation.status_code == 200
    assert validation.json()["status"] == "VALID"

    compiled = client.post(
        "/api/chatbi/query/compile",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "dsl": validation.json()["normalized_dsl"],
            "permission_context": policy,
        },
    ).json()
    execute_headers = {**service_headers, "Idempotency-Key": compiled["query_id"]}
    executed = client.post(
        "/api/chatbi/query/execute",
        headers=execute_headers,
        json={
            "workspace_id": "demo",
            "operator_id": "public_demo_user",
            "query_id": compiled["query_id"],
            "execution_token": compiled["execution_token"],
        },
    )
    assert executed.status_code == 200, executed.text
    result = executed.json()
    assert result["row_count"] == 4

    profiled = client.post(
        "/api/chatbi/result/profile",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "query_id": compiled["query_id"],
            "execution_result": result,
            "dsl": validation.json()["normalized_dsl"],
        },
    )
    assert profiled.status_code == 200, profiled.text
    profile = profiled.json()
    assert profile["chart_spec"]["type"] == "bar"
    contributions = profile["dimension_contributions"]
    assert len(contributions) == 4
    assert [item["rank"] for item in contributions] == [1, 2, 3, 4]
    assert abs(sum(item["share"] for item in contributions) - 1.0) < 0.00001
    assert all(item["dimension_id"] == "D_REGION" for item in contributions)
