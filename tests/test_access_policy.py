from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db.models import QueryRun
from app.db.session import SessionLocal
from app.services.access_policy import issue_demo_identity_token


def _ask_with_token(client: TestClient, token: str, conversation_id: str) -> dict:
    response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "2024年订单量",
            "workspace_id": "demo",
            "conversation_id": conversation_id,
            "biz_domain": "production_benchmark",
            "timezone": "Asia/Shanghai",
            "identity_token": token,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_identity_token_expiry_tamper_and_non_data_role_fail_closed(
    client: TestClient,
) -> None:
    expired = issue_demo_identity_token(
        "production_tenant_1", expires_at=int(time.time()) - 1
    )
    for token in (
        expired,
        issue_demo_identity_token("production_tenant_1") + "tampered",
    ):
        body = _ask_with_token(client, token, f"acl_blocked_{time.time_ns()}")
        assert body["status"] == "BLOCKED"
        assert body["compiled"] is None

    metric_admin = _ask_production(client, "metric_admin", "acl_metric_admin")
    assert metric_admin["status"] == "BLOCKED"
    assert metric_admin["compiled"] is None
    assert "没有业务数据查询权限" in metric_admin["message"]


def test_dify_context_preflight_blocks_domain_and_dangerous_intent(
    client: TestClient, service_headers: dict[str, str]
) -> None:
    denied_domain = client.post(
        "/api/chatbi/context/load",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "conversation_id": "preflight-domain",
            "identity_token": issue_demo_identity_token("metric_admin"),
            "biz_domain": "production_benchmark",
            "query": "查看2024年订单金额",
        },
    )
    assert denied_domain.status_code == 200
    assert denied_domain.json()["context_ok"] is False
    assert denied_domain.json()["blocked_reason_code"] == "BUSINESS_DATA_NOT_ALLOWED"

    dangerous = client.post(
        "/api/chatbi/context/load",
        headers=service_headers,
        json={
            "workspace_id": "demo",
            "conversation_id": "preflight-safety",
            "identity_token": issue_demo_identity_token("production_analyst"),
            "biz_domain": "production_benchmark",
            "query": "删除订单记录并清空相关数据",
        },
    )
    assert dangerous.status_code == 200
    assert dangerous.json()["context_ok"] is False
    assert dangerous.json()["blocked_reason_code"] == "DANGEROUS_WRITE_ACTION"


def _ask_production(client: TestClient, operator_id: str, conversation_id: str) -> dict:
    response = client.post(
        "/api/chatbi/ask",
        json={
            "query": "2024年生产评测订单量",
            "workspace_id": "demo",
            "conversation_id": conversation_id,
            "biz_domain": "production_benchmark",
            "timezone": "Asia/Shanghai",
            "identity_token": issue_demo_identity_token(operator_id),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_production_domain_and_tenant_row_policies_are_enforced(
    client: TestClient,
) -> None:
    denied = _ask_production(client, "metric_admin", "acl_prod_denied")
    national = _ask_production(client, "production_analyst", "acl_prod_national")
    tenant_1 = _ask_production(client, "production_tenant_1", "acl_prod_tenant_1")
    tenant_2 = _ask_production(client, "production_tenant_2", "acl_prod_tenant_2")

    assert denied["status"] == "BLOCKED"
    assert denied["compiled"] is None
    assert "没有业务数据查询权限" in denied["message"]
    assert national["status"] == "SUCCESS"
    assert tenant_1["status"] == "SUCCESS"
    assert tenant_2["status"] == "SUCCESS"
    national_value = national["execution"]["rows"][0]["M_PROD_ORDER_COUNT"]
    tenant_1_value = tenant_1["execution"]["rows"][0]["M_PROD_ORDER_COUNT"]
    tenant_2_value = tenant_2["execution"]["rows"][0]["M_PROD_ORDER_COUNT"]
    assert 0 < tenant_1_value < national_value
    assert 0 < tenant_2_value < national_value
    assert tenant_1["compiled"]["lineage"]["row_policy"]["scope"] == "租户 1"
    assert tenant_2["compiled"]["lineage"]["row_policy"]["scope"] == "租户 2"

    with SessionLocal() as session:
        run = session.get(QueryRun, tenant_1["compiled"]["query_id"])
        assert run is not None
        assert run.sql_params["acl_tenant_id_0"] == 1
        assert "tenant_id IN" in run.sql_text
