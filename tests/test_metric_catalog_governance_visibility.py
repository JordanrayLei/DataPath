from __future__ import annotations

from app.db.models import BusinessDomain, Metric, MetricVersion, SemanticModel
from app.db.session import SessionLocal


def test_governance_catalog_shows_blocked_metric_as_read_only(
    client,
    service_headers,
) -> None:
    domain_id = "test_degraded_catalog"
    model_id = "SM_TEST_DEGRADED_CATALOG"
    metric_id = "M_TEST_DEGRADED_CATALOG"
    with SessionLocal() as session:
        session.add(
            BusinessDomain(
                id=domain_id,
                name="测试异常业务域",
                description="验证治理目录可见性",
                owner="test",
                business_goal="验证异常资产只读展示",
                status="DEGRADED",
            )
        )
        session.add(
            SemanticModel(
                id=model_id,
                business_domain_id=domain_id,
                name="测试异常模型",
                warehouse="clickhouse",
                physical_table="test_catalog.fct_orders",
                default_time_field="business_date",
                fields_json=["business_date", "amount"],
                status="DEGRADED",
            )
        )
        session.add(
            Metric(
                id=metric_id,
                business_domain_id=domain_id,
                name="测试异常指标",
                description="用于验证异常指标在治理中心可见",
                metric_type="amount",
                unit="CNY",
                owner="test",
                status="BLOCKED",
            )
        )
        session.flush()
        session.add(
            MetricVersion(
                metric_id=metric_id,
                version=1,
                semantic_model_id=model_id,
                expression_json={"op": "sum", "field": "amount"},
                time_dimension_id="D_DATE",
                status="PUBLISHED",
            )
        )
        session.commit()

    try:
        runtime_response = client.get(
            "/api/chatbi/metrics/catalog",
            params={"workspace_id": "demo", "domain": domain_id},
            headers=service_headers,
        )
        assert runtime_response.status_code == 200, runtime_response.text
        assert runtime_response.json()["items"] == []

        governance_response = client.get(
            "/api/chatbi/metrics/catalog",
            params={
                "workspace_id": "demo",
                "domain": domain_id,
                "visibility": "governance",
            },
            headers=service_headers,
        )
        assert governance_response.status_code == 200, governance_response.text
        item = governance_response.json()["items"][0]
        assert item["metric_id"] == metric_id
        assert item["status"] == "BLOCKED"
        assert item["business_domain_status"] == "DEGRADED"
        assert item["semantic_model_status"] == "DEGRADED"
        assert item["read_only"] is True
        assert item["governance_blockers"]

        detail_response = client.get(
            f"/api/chatbi/metrics/catalog/{metric_id}",
            params={"workspace_id": "demo", "visibility": "governance"},
            headers=service_headers,
        )
        assert detail_response.status_code == 200, detail_response.text
        assert detail_response.json()["metric"]["read_only"] is True
    finally:
        with SessionLocal() as session:
            session.query(MetricVersion).filter(
                MetricVersion.metric_id == metric_id
            ).delete()
            session.query(Metric).filter(Metric.id == metric_id).delete()
            session.query(SemanticModel).filter(
                SemanticModel.id == model_id
            ).delete()
            session.query(BusinessDomain).filter(
                BusinessDomain.id == domain_id
            ).delete()
            session.commit()
