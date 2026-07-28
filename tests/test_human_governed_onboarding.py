from __future__ import annotations

from sqlalchemy import delete

from app.db.models import (
    BusinessDomain,
    BusinessDomainTableBinding,
    Metric,
    MetricDraft,
    PhysicalTableAsset,
    SemanticEntity,
    SemanticModel,
    WarehouseSource,
)
from app.db.session import SessionLocal


def test_ai_preheat_requires_human_apply_and_does_not_change_formula(client, monkeypatch) -> None:
    metric_id = "M_TEST_HUMAN_PREHEAT"
    payload = {
        "workspace_id": "demo",
        "metric_id": metric_id,
        "business_domain_id": "production_benchmark",
        "name": "人工治理预热测试指标",
        "description": "统计支付事实表中的支付金额，仅用于验证 AI 只生成检索语义而不修改业务公式。",
        "metric_type": "amount",
        "unit": "CNY",
        "owner": "metric-admin",
        "aliases": [],
        "positive_examples": [],
        "negative_examples": [],
        "semantic_model_id": "SM_PROD_ORDERS",
        "expression": {"op": "sum", "field": "gross_amount"},
        "default_aggregation": "default",
        "time_dimension_id": "D_DATE",
        "dimension_ids": ["D_DATE"],
    }
    saved = client.put(f"/api/chatbi/metrics/manage/drafts/{metric_id}", json=payload)
    assert saved.status_code == 200, saved.text

    monkeypatch.setattr(
        "app.services.metric_preheat._call_deepseek",
        lambda metadata: {
            "aliases": ["支付总额", "成交支付金额"],
            "positive_examples": ["最近一个月支付总额"],
            "negative_examples": ["最近一个月退款金额"],
        },
    )
    generated = client.post(
        f"/api/chatbi/metrics/manage/drafts/{metric_id}/preheat/generate",
        json={"workspace_id": "demo", "operator_id": "metric_admin"},
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["proposal"]["status"] == "PROPOSED"

    drafts = client.get("/api/chatbi/metrics/manage/drafts?workspace_id=demo").json()["items"]
    draft = next(item for item in drafts if item["metric_id"] == metric_id)
    assert draft["aliases"] == []
    assert draft["expression"] == {"op": "sum", "field": "gross_amount"}

    applied = client.post(
        f"/api/chatbi/metrics/manage/drafts/{metric_id}/preheat/apply",
        json={
            "workspace_id": "demo",
            "operator_id": "human_reviewer",
            "aliases": ["支付总额"],
            "positive_examples": ["最近一个月支付总额"],
            "negative_examples": ["最近一个月退款金额"],
        },
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["proposal"]["status"] == "HUMAN_APPLIED"

    with SessionLocal() as session:
        session.execute(delete(MetricDraft).where(MetricDraft.metric_id == metric_id))
        session.execute(delete(Metric).where(Metric.id == metric_id))
        session.commit()


def test_scanned_source_cannot_publish_before_human_confirmation(client) -> None:
    source_id = "test_human_governed_source"
    model_id = "SM_TEST_HUMAN_ORDERS"
    entity_id = "E_TEST_HUMAN_ORDERS"
    connection_payload = {
        "workspace_id": "demo",
        "name": "人工治理测试数据源",
        "kind": "clickhouse",
        "operator_id": "metric_admin",
        "connection": {
            "host": "127.0.0.1",
            "port": 8123,
            "database": "production_benchmark",
            "username": "chatbi_reader",
            "credential_env": "CLICKHOUSE_READER_PASSWORD",
        },
    }
    saved = client.put(f"/api/chatbi/governance/sources/{source_id}", json=connection_payload)
    assert saved.status_code == 200, saved.text
    blocked = client.post(
        f"/api/chatbi/governance/sources/{source_id}/publish",
        json={"workspace_id": "demo", "operator_id": "metric_admin"},
    )
    assert blocked.status_code == 422
    assert "human confirmation" in blocked.text

    with SessionLocal() as session:
        source = session.get(WarehouseSource, source_id)
        source.scan_snapshot_json = {
            "database": "production_benchmark",
            "tables": [
                {
                    "name": "fct_orders",
                    "columns": [
                        {"name": "order_id", "type": "UInt64", "position": 1},
                        {"name": "purchase_ts", "type": "DateTime", "position": 2},
                        {"name": "gross_amount", "type": "Decimal", "position": 3},
                    ],
                }
            ],
        }
        source.status = "SCANNED"
        session.commit()


    confirmed = client.put(
        f"/api/chatbi/governance/sources/{source_id}/confirmation",
        json={
            "workspace_id": "demo",
            "business_domain_id": "human_onboarding_test",
            "business_domain_name": "人工接入测试域",
            "tables": [
                {
                    "table": "fct_orders",
                    "enabled": True,
                    "semantic_model_id": model_id,
                    "model_name": "人工确认订单",
                    "entity_id": entity_id,
                    "entity_name": "人工确认订单",
                    "entity_type": "fact",
                    "grain": "每行一笔订单",
                    "primary_keys": ["order_id"],
                    "default_time_field": "purchase_ts",
                }
            ],
            "operator_id": "human_reviewer",
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    published = client.post(
        f"/api/chatbi/governance/sources/{source_id}/publish",
        json={"workspace_id": "demo", "operator_id": "human_reviewer"},
    )
    assert published.status_code == 200, published.text
    assert published.json()["source"]["status"] == "PUBLISHED"

    with SessionLocal() as session:
        model = session.get(SemanticModel, model_id)
        assert model.fields_json == ["order_id", "purchase_ts", "gross_amount"]
        session.execute(delete(SemanticEntity).where(SemanticEntity.id == entity_id))
        session.execute(delete(SemanticModel).where(SemanticModel.id == model_id))
        session.execute(delete(WarehouseSource).where(WarehouseSource.id == source_id))
        session.execute(
            delete(BusinessDomain).where(BusinessDomain.id == "human_onboarding_test")
        )
        session.commit()


def test_business_domain_can_be_created_before_table_assignment(client) -> None:
    domain_id = "test_frontend_domain_flow"
    response = client.put(
        f"/api/chatbi/governance/domains/{domain_id}",
        json={
            "workspace_id": "demo",
            "name": "前端流程测试域",
            "description": "用于验证业务域可以在选择物理表之前独立创建。",
            "owner": "metric-admin",
            "business_goal": "验证从数据资产到业务域再到指标的治理流程。",
            "operator_id": "metric_admin",
        },
    )
    assert response.status_code == 200, response.text
    domain = response.json()["domain"]
    assert domain["id"] == domain_id
    assert domain["status"] == "DRAFT"
    assert domain["readiness_score"] == 20
    assert domain["stage_status"]["boundary"] == "DONE"
    assert domain["stage_status"]["models"] == "BLOCKED"
    assert domain["can_create_metric"] is False
    assert domain["blockers"]
    assert domain["model_count"] == 0
    assert domain["metric_count"] == 0

    listed = client.get("/api/chatbi/governance/domains?workspace_id=demo")
    assert listed.status_code == 200, listed.text
    assert domain_id in {item["id"] for item in listed.json()["items"]}

    with SessionLocal() as session:
        session.execute(delete(BusinessDomain).where(BusinessDomain.id == domain_id))
        session.commit()


def test_physical_table_assets_are_read_only_and_domain_neutral(client) -> None:
    assets = client.get("/api/chatbi/governance/assets?workspace_id=demo")
    assert assets.status_code == 200, assets.text
    asset = next(
        item
        for item in assets.json()["items"]
        if item["physical_table"] == "production_benchmark.fct_orders"
    )
    assert "governance" not in asset
    assert asset["columns"]
    response = client.put(
        f"/api/chatbi/governance/assets/{asset['id']}",
        json={"workspace_id": "demo"},
    )
    assert response.status_code == 404


def test_one_physical_table_can_be_published_to_multiple_business_domains(client) -> None:
    domain_id = "test_shared_physical_asset"
    created = client.put(
        f"/api/chatbi/governance/domains/{domain_id}",
        json={
            "workspace_id": "demo",
            "name": "共享物理资产测试域",
            "description": "验证同一物理表可被多个业务域独立治理。",
            "owner": "metric-admin",
            "business_goal": "复用生产订单表但维护独立语义模型。",
            "operator_id": "metric_admin",
        },
    )
    assert created.status_code == 200, created.text

    assets = client.get("/api/chatbi/governance/assets?workspace_id=demo")
    assert assets.status_code == 200, assets.text
    asset = next(
        item
        for item in assets.json()["items"]
        if item["physical_table"] == "production_benchmark.fct_orders"
    )
    fields = [item["name"] for item in asset["columns"]]
    assert "order_id" in fields

    model_id = "SM_TEST_SHARED_ORDERS"
    entity_id = "E_TEST_SHARED_ORDERS"
    payload = {
        "workspace_id": "demo",
        "operator_id": "metric_admin",
        "tables": [
            {
                "physical_asset_id": asset["id"],
                "semantic_model_id": model_id,
                "model_name": "共享订单业务视图",
                "entity_id": entity_id,
                "entity_name": "共享订单",
                "entity_type": "fact",
                "grain": "每行一笔订单",
                "primary_keys": ["order_id"],
                "default_time_field": "business_date",
                "exposed_fields": fields,
            }
        ],
    }
    confirmed = client.put(
        f"/api/chatbi/governance/domains/{domain_id}/table-bindings",
        json=payload,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["items"][0]["status"] == "CONFIRMED"

    published = client.post(
        f"/api/chatbi/governance/domains/{domain_id}/table-bindings/publish",
        json={"workspace_id": "demo", "operator_id": "metric_admin"},
    )
    assert published.status_code == 200, published.text
    assert published.json()["items"][0]["status"] == "PUBLISHED"

    with SessionLocal() as session:
        shared_model = session.get(SemanticModel, model_id)
        original_model = session.get(SemanticModel, "SM_PROD_ORDERS")
        assert shared_model is not None
        assert original_model is not None
        assert shared_model.physical_table == original_model.physical_table
        assert shared_model.business_domain_id != original_model.business_domain_id
        session.execute(delete(SemanticEntity).where(SemanticEntity.id == entity_id))
        session.execute(delete(SemanticModel).where(SemanticModel.id == model_id))
        session.execute(
            delete(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.business_domain_id == domain_id
            )
        )
        session.execute(delete(BusinessDomain).where(BusinessDomain.id == domain_id))
        session.commit()


def test_domain_selection_and_single_model_publication_are_separate(client) -> None:
    domain_id = "test_model_draft_flow"
    created = client.put(
        f"/api/chatbi/governance/domains/{domain_id}",
        json={
            "workspace_id": "demo",
            "name": "模型草稿流程测试域",
            "description": "验证选表、模型草稿和单模型发布彼此分离。",
            "owner": "metric-admin",
            "business_goal": "只在显式发布后更新运行时语义模型。",
            "operator_id": "metric_admin",
        },
    )
    assert created.status_code == 200, created.text
    assets = client.get("/api/chatbi/governance/assets?workspace_id=demo").json()["items"]
    asset = next(
        item
        for item in assets
        if item["physical_table"] == "production_benchmark.fct_orders"
    )
    fields = [item["name"] for item in asset["columns"]]
    selected = client.put(
        f"/api/chatbi/governance/domains/{domain_id}/table-selections",
        json={
            "workspace_id": "demo",
            "physical_asset_ids": [asset["id"]],
            "operator_id": "metric_admin",
        },
    )
    assert selected.status_code == 200, selected.text
    binding = selected.json()["items"][0]
    assert binding["status"] == "CONFIRMED"
    assert binding["version"] == 0
    with SessionLocal() as session:
        assert session.get(SemanticModel, binding["semantic_model_id"]) is None

    saved = client.put(
        f"/api/chatbi/governance/domains/{domain_id}/models/{binding['id']}",
        json={
            "workspace_id": "demo",
            "model_name": "域内订单分析模型",
            "description": "只属于模型草稿流程测试域的订单解释。",
            "entity_type": "fact",
            "grain": "每行一笔域内订单",
            "primary_keys": ["order_id"],
            "default_time_field": "business_date",
            "exposed_fields": ["order_id", "business_date", "net_amount"],
            "operator_id": "metric_admin",
        },
    )
    assert saved.status_code == 200, saved.text
    draft = saved.json()["items"][0]
    assert draft["status"] == "CONFIRMED"
    assert draft["version"] == 0
    assert draft["description"] == "只属于模型草稿流程测试域的订单解释。"
    assert draft["grain"] == "每行一笔域内订单"
    assert set(draft["exposed_fields"]) < set(fields)

    published = client.post(
        f"/api/chatbi/governance/domains/{domain_id}/models/{binding['id']}/publish",
        json={"workspace_id": "demo", "operator_id": "metric_admin"},
    )
    assert published.status_code == 200, published.text
    active = published.json()["items"][0]
    assert active["status"] == "PUBLISHED"
    assert active["version"] == 1
    with SessionLocal() as session:
        model = session.get(SemanticModel, binding["semantic_model_id"])
        assert model is not None
        assert model.name == "域内订单分析模型"
        assert model.fields_json == ["order_id", "business_date", "net_amount"]
        session.execute(
            delete(SemanticEntity).where(
                SemanticEntity.semantic_model_id == binding["semantic_model_id"]
            )
        )
        session.execute(
            delete(SemanticModel).where(SemanticModel.id == binding["semantic_model_id"])
        )
        session.execute(
            delete(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.business_domain_id == domain_id
            )
        )
        session.execute(delete(BusinessDomain).where(BusinessDomain.id == domain_id))
        session.commit()
