from __future__ import annotations

import hashlib
import json

import pytest
from sqlalchemy import delete, select

from app.db.models import (
    BusinessDomain,
    BusinessDomainTableBinding,
    Metric,
    MetricVersion,
    PhysicalTableAsset,
    SchemaChangeEvent,
    SemanticEntity,
    SemanticJoinRelation,
    SemanticModel,
    WarehouseSource,
)
from app.db.session import SessionLocal
from app.schemas.governance import BusinessDomainModelUpdateRequest
from app.services.warehouse_governance import (
    _upsert_scanned_assets,
    list_business_domains,
    publish_domain_semantic_model,
    update_domain_semantic_model,
)


def _columns(*items: tuple[str, str]) -> list[dict]:
    return [
        {"name": name, "type": field_type, "position": index}
        for index, (name, field_type) in enumerate(items, start=1)
    ]


def _schema_hash(columns: list[dict]) -> str:
    canonical = json.dumps(
        columns, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _setup_graph(suffix: str) -> dict[str, str]:
    ids = {
        "domain": f"schema_impact_{suffix}",
        "source": f"schema_impact_source_{suffix}",
        "fact_asset": f"PTA_SCHEMA_FACT_{suffix}",
        "dim_asset": f"PTA_SCHEMA_DIM_{suffix}",
        "binding": f"DTB_SCHEMA_FACT_{suffix}",
        "dim_binding": f"DTB_SCHEMA_DIM_{suffix}",
        "model": f"SM_SCHEMA_FACT_{suffix.upper()}",
        "dim_model": f"SM_SCHEMA_DIM_{suffix.upper()}",
        "entity": f"E_SCHEMA_FACT_{suffix.upper()}",
        "dim_entity": f"E_SCHEMA_DIM_{suffix.upper()}",
        "relation": f"J_SCHEMA_{suffix.upper()}",
        "metric": f"M_SCHEMA_{suffix.upper()}",
    }
    fact_columns = _columns(
        ("order_id", "UInt64"),
        ("customer_id", "UInt64"),
        ("event_date", "Date"),
        ("amount", "Decimal(18,2)"),
    )
    dim_columns = _columns(("customer_id", "UInt64"), ("customer_name", "String"))
    with SessionLocal() as session:
        session.add(
            BusinessDomain(
                id=ids["domain"],
                name=f"结构影响测试 {suffix}",
                description="隔离验证结构变化影响传播。",
                owner="test",
                business_goal="验证失败关闭和恢复。",
                status="ACTIVE",
            )
        )
        session.add(
            WarehouseSource(
                id=ids["source"],
                workspace_id="demo",
                name=f"Schema impact {suffix}",
                kind="clickhouse",
                business_domain_id=ids["domain"],
                connection_json={"database": f"schema_impact_{suffix}"},
                scan_snapshot_json={},
                governance_json={},
                status="PUBLISHED",
                created_by="test",
            )
        )
        session.flush()
        session.add_all(
            [
                PhysicalTableAsset(
                    id=ids["fact_asset"],
                    source_id=ids["source"],
                    database_name=f"schema_impact_{suffix}",
                    table_name="fct_orders",
                    physical_table=f"schema_impact_{suffix}.fct_orders",
                    columns_json=fact_columns,
                    schema_sha256=_schema_hash(fact_columns),
                    status="ACTIVE",
                ),
                PhysicalTableAsset(
                    id=ids["dim_asset"],
                    source_id=ids["source"],
                    database_name=f"schema_impact_{suffix}",
                    table_name="dim_customer",
                    physical_table=f"schema_impact_{suffix}.dim_customer",
                    columns_json=dim_columns,
                    schema_sha256=_schema_hash(dim_columns),
                    status="ACTIVE",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                SemanticModel(
                    id=ids["model"],
                    business_domain_id=ids["domain"],
                    name="订单事实",
                    warehouse="clickhouse",
                    physical_table=f"schema_impact_{suffix}.fct_orders",
                    default_time_field="event_date",
                    fields_json=[item["name"] for item in fact_columns],
                    status="ACTIVE",
                ),
                SemanticModel(
                    id=ids["dim_model"],
                    business_domain_id=ids["domain"],
                    name="客户维度",
                    warehouse="clickhouse",
                    physical_table=f"schema_impact_{suffix}.dim_customer",
                    default_time_field="",
                    fields_json=[item["name"] for item in dim_columns],
                    status="ACTIVE",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                SemanticEntity(
                    id=ids["entity"],
                    semantic_model_id=ids["model"],
                    business_domain_id=ids["domain"],
                    name="订单事实",
                    grain="每行一笔订单",
                    primary_key_json=["order_id"],
                    entity_type="fact",
                    status="ACTIVE",
                ),
                SemanticEntity(
                    id=ids["dim_entity"],
                    semantic_model_id=ids["dim_model"],
                    business_domain_id=ids["domain"],
                    name="客户维度",
                    grain="每行一个客户",
                    primary_key_json=["customer_id"],
                    entity_type="dimension",
                    status="ACTIVE",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                BusinessDomainTableBinding(
                    id=ids["binding"],
                    business_domain_id=ids["domain"],
                    physical_asset_id=ids["fact_asset"],
                    semantic_model_id=ids["model"],
                    model_name="订单事实",
                    description="订单金额分析。",
                    entity_id=ids["entity"],
                    entity_name="订单事实",
                    entity_type="fact",
                    grain="每行一笔订单",
                    primary_keys_json=["order_id"],
                    default_time_field="event_date",
                    exposed_fields_json=[item["name"] for item in fact_columns],
                    schema_contract_json={
                        item["name"]: item["type"] for item in fact_columns
                    },
                    status="PUBLISHED",
                    version=1,
                    created_by="test",
                ),
                BusinessDomainTableBinding(
                    id=ids["dim_binding"],
                    business_domain_id=ids["domain"],
                    physical_asset_id=ids["dim_asset"],
                    semantic_model_id=ids["dim_model"],
                    model_name="客户维度",
                    description="客户属性。",
                    entity_id=ids["dim_entity"],
                    entity_name="客户维度",
                    entity_type="dimension",
                    grain="每行一个客户",
                    primary_keys_json=["customer_id"],
                    default_time_field="",
                    exposed_fields_json=[item["name"] for item in dim_columns],
                    schema_contract_json={
                        item["name"]: item["type"] for item in dim_columns
                    },
                    status="PUBLISHED",
                    version=1,
                    created_by="test",
                ),
                SemanticJoinRelation(
                    id=ids["relation"],
                    business_domain_id=ids["domain"],
                    left_entity_id=ids["entity"],
                    right_entity_id=ids["dim_entity"],
                    left_keys_json=["customer_id"],
                    right_keys_json=["customer_id"],
                    relationship_type="many_to_one",
                    join_type="left",
                    fanout_strategy="safe",
                    priority=10,
                    status="PUBLISHED",
                    version=1,
                ),
                Metric(
                    id=ids["metric"],
                    business_domain_id=ids["domain"],
                    name="订单金额",
                    description="测试结构变化传播。",
                    metric_type="amount",
                    unit="CNY",
                    owner="test",
                    status="PUBLISHED",
                ),
            ]
        )
        session.flush()
        session.add(
            MetricVersion(
                metric_id=ids["metric"],
                version=1,
                semantic_model_id=ids["model"],
                expression_json={"op": "sum", "field": "amount"},
                default_aggregation="sum",
                time_dimension_id="D_DATE",
                status="PUBLISHED",
            )
        )
        session.commit()
    return ids


def _cleanup_graph(ids: dict[str, str]) -> None:
    with SessionLocal() as session:
        session.execute(
            delete(SchemaChangeEvent).where(SchemaChangeEvent.source_id == ids["source"])
        )
        session.execute(
            delete(MetricVersion).where(MetricVersion.metric_id == ids["metric"])
        )
        session.execute(delete(Metric).where(Metric.id == ids["metric"]))
        session.execute(
            delete(SemanticJoinRelation).where(
                SemanticJoinRelation.id == ids["relation"]
            )
        )
        session.execute(
            delete(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.business_domain_id == ids["domain"]
            )
        )
        session.execute(
            delete(SemanticEntity).where(
                SemanticEntity.business_domain_id == ids["domain"]
            )
        )
        session.execute(
            delete(SemanticModel).where(
                SemanticModel.business_domain_id == ids["domain"]
            )
        )
        session.execute(
            delete(PhysicalTableAsset).where(
                PhysicalTableAsset.source_id == ids["source"]
            )
        )
        session.execute(delete(WarehouseSource).where(WarehouseSource.id == ids["source"]))
        session.execute(delete(BusinessDomain).where(BusinessDomain.id == ids["domain"]))
        session.commit()


@pytest.mark.parametrize("scenario", ["table_removed", "field_removed", "type_changed"])
def test_breaking_schema_changes_fail_closed_across_lineage(scenario: str) -> None:
    ids = _setup_graph(scenario)
    try:
        dim_columns = _columns(("customer_id", "UInt64"), ("customer_name", "String"))
        if scenario == "table_removed":
            grouped = {"dim_customer": dim_columns}
            expected_type = "TABLE_REMOVED"
        elif scenario == "field_removed":
            grouped = {
                "fct_orders": _columns(
                    ("order_id", "UInt64"),
                    ("customer_id", "UInt64"),
                    ("event_date", "Date"),
                ),
                "dim_customer": dim_columns,
            }
            expected_type = "BREAKING_COLUMNS"
        else:
            grouped = {
                "fct_orders": _columns(
                    ("order_id", "UInt64"),
                    ("customer_id", "UInt64"),
                    ("event_date", "Date"),
                    ("amount", "String"),
                ),
                "dim_customer": dim_columns,
            }
            expected_type = "BREAKING_COLUMNS"
        with SessionLocal() as session:
            source = session.get(WarehouseSource, ids["source"])
            events = _upsert_scanned_assets(
                session, source, f"schema_impact_{scenario}", grouped
            )
            source.status = "DEGRADED"
            session.commit()
            assert len(events) == 1
            event = events[0]
            assert event.change_type == expected_type
            assert event.status == "OPEN"
            assert event.impact_json["model_ids"] == [ids["model"]]
            assert event.impact_json["relation_ids"] == [ids["relation"]]
            assert event.impact_json["metric_ids"] == [ids["metric"]]
            assert session.get(BusinessDomainTableBinding, ids["binding"]).status == "IMPACTED"
            assert session.get(SemanticModel, ids["model"]).status == "DEGRADED"
            assert session.get(SemanticEntity, ids["entity"]).status == "DEGRADED"
            assert session.get(SemanticJoinRelation, ids["relation"]).status == "BLOCKED"
            assert session.get(Metric, ids["metric"]).status == "BLOCKED"
            assert session.get(BusinessDomain, ids["domain"]).status == "DEGRADED"
            domain = next(
                item
                for item in list_business_domains(session, "demo")
                if item.id == ids["domain"]
            )
            assert domain.status == "DEGRADED"
            assert domain.stage_status["data"] == "BLOCKED"
            assert domain.stage_status["models"] == "BLOCKED"
            assert domain.stage_status["relations"] == "BLOCKED"
            assert domain.stage_status["metrics"] == "BLOCKED"
            assert any("受影响模型" in blocker for blocker in domain.blockers)
    finally:
        _cleanup_graph(ids)


def test_reviewed_type_change_can_be_republished_and_restores_dependents() -> None:
    ids = _setup_graph("recovery")
    try:
        changed_columns = _columns(
            ("order_id", "UInt64"),
            ("customer_id", "UInt64"),
            ("event_date", "Date"),
            ("amount", "Float64"),
        )
        dim_columns = _columns(("customer_id", "UInt64"), ("customer_name", "String"))
        with SessionLocal() as session:
            source = session.get(WarehouseSource, ids["source"])
            _upsert_scanned_assets(
                session,
                source,
                "schema_impact_recovery",
                {"fct_orders": changed_columns, "dim_customer": dim_columns},
            )
            source.status = "DEGRADED"
            session.commit()
            payload = BusinessDomainModelUpdateRequest(
                workspace_id="demo",
                model_name="订单事实",
                description="已确认 amount 改为 Float64。",
                entity_type="fact",
                grain="每行一笔订单",
                primary_keys=["order_id"],
                default_time_field="event_date",
                exposed_fields=[item["name"] for item in changed_columns],
                operator_id="metric_admin",
            )
            update_domain_semantic_model(
                session, ids["domain"], ids["binding"], payload
            )
            publish_domain_semantic_model(
                session, ids["domain"], ids["binding"], "demo"
            )
            assert session.get(BusinessDomainTableBinding, ids["binding"]).status == "PUBLISHED"
            assert session.get(SemanticModel, ids["model"]).status == "ACTIVE"
            assert session.get(SemanticJoinRelation, ids["relation"]).status == "PUBLISHED"
            assert session.get(Metric, ids["metric"]).status == "PUBLISHED"
            event = session.scalar(
                select(SchemaChangeEvent).where(
                    SchemaChangeEvent.source_id == ids["source"]
                )
            )
            assert event.status == "RESOLVED"
            assert session.get(PhysicalTableAsset, ids["fact_asset"]).status == "ACTIVE"
    finally:
        _cleanup_graph(ids)


def test_restored_table_can_be_reviewed_and_unblocks_dependents() -> None:
    ids = _setup_graph("table_restore")
    fact_columns = _columns(
        ("order_id", "UInt64"),
        ("customer_id", "UInt64"),
        ("event_date", "Date"),
        ("amount", "Decimal(18,2)"),
    )
    dim_columns = _columns(("customer_id", "UInt64"), ("customer_name", "String"))
    try:
        with SessionLocal() as session:
            source = session.get(WarehouseSource, ids["source"])
            _upsert_scanned_assets(
                session,
                source,
                "schema_impact_table_restore",
                {"dim_customer": dim_columns},
            )
            source.status = "DEGRADED"
            session.commit()

        with SessionLocal() as session:
            source = session.get(WarehouseSource, ids["source"])
            events = _upsert_scanned_assets(
                session,
                source,
                "schema_impact_table_restore",
                {"fct_orders": fact_columns, "dim_customer": dim_columns},
            )
            assert any(event.change_type == "TABLE_RESTORED" for event in events)
            payload = BusinessDomainModelUpdateRequest(
                workspace_id="demo",
                model_name="订单事实",
                description="物理表恢复后已人工复核。",
                entity_type="fact",
                grain="每行一笔订单",
                primary_keys=["order_id"],
                default_time_field="event_date",
                exposed_fields=[item["name"] for item in fact_columns],
                operator_id="metric_admin",
            )
            update_domain_semantic_model(
                session, ids["domain"], ids["binding"], payload
            )
            publish_domain_semantic_model(
                session, ids["domain"], ids["binding"], "demo"
            )
            assert session.get(PhysicalTableAsset, ids["fact_asset"]).status == "ACTIVE"
            assert session.get(SemanticModel, ids["model"]).status == "ACTIVE"
            assert session.get(SemanticJoinRelation, ids["relation"]).status == "PUBLISHED"
            assert session.get(Metric, ids["metric"]).status == "PUBLISHED"
            breaking_event = session.scalar(
                select(SchemaChangeEvent).where(
                    SchemaChangeEvent.source_id == ids["source"],
                    SchemaChangeEvent.change_type == "TABLE_REMOVED",
                )
            )
            assert breaking_event.status == "RESOLVED"
    finally:
        _cleanup_graph(ids)


def test_removed_metric_field_stays_blocked_until_metric_is_revised() -> None:
    ids = _setup_graph("metric_repair_required")
    changed_columns = _columns(
        ("order_id", "UInt64"),
        ("customer_id", "UInt64"),
        ("event_date", "Date"),
    )
    dim_columns = _columns(("customer_id", "UInt64"), ("customer_name", "String"))
    try:
        with SessionLocal() as session:
            source = session.get(WarehouseSource, ids["source"])
            _upsert_scanned_assets(
                session,
                source,
                "schema_impact_metric_repair_required",
                {"fct_orders": changed_columns, "dim_customer": dim_columns},
            )
            source.status = "DEGRADED"
            session.commit()
            payload = BusinessDomainModelUpdateRequest(
                workspace_id="demo",
                model_name="订单事实",
                description="确认 amount 字段已经从物理表移除。",
                entity_type="fact",
                grain="每行一笔订单",
                primary_keys=["order_id"],
                default_time_field="event_date",
                exposed_fields=[item["name"] for item in changed_columns],
                operator_id="metric_admin",
            )
            update_domain_semantic_model(
                session, ids["domain"], ids["binding"], payload
            )
            publish_domain_semantic_model(
                session, ids["domain"], ids["binding"], "demo"
            )
            assert session.get(SemanticModel, ids["model"]).status == "ACTIVE"
            assert session.get(SemanticJoinRelation, ids["relation"]).status == "PUBLISHED"
            assert session.get(Metric, ids["metric"]).status == "BLOCKED"
            event = session.scalar(
                select(SchemaChangeEvent).where(
                    SchemaChangeEvent.source_id == ids["source"],
                    SchemaChangeEvent.change_type == "BREAKING_COLUMNS",
                )
            )
            assert event.status == "OPEN"
    finally:
        _cleanup_graph(ids)
