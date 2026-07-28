"""Run destructive schema-change acceptance tests against an isolated ClickHouse database.

The script creates a dedicated database and governance graph, mutates the physical
schema with real DDL, invokes the public scan/model APIs, verifies fail-closed
propagation and recovery, writes a JSON report, and removes every test resource.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import get_settings
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
from app.main import app
from scripts.clickhouse_http import ClickHouseHttpClient


DATABASE = "datapath_schema_ddl_acceptance"
SOURCE_ID = "schema_ddl_acceptance_source"
DOMAIN_ID = "schema_ddl_acceptance"
BINDING_ID = "DTB_SCHEMA_DDL_FACT"
DIM_BINDING_ID = "DTB_SCHEMA_DDL_DIM"
MODEL_ID = "SM_SCHEMA_DDL_FACT"
DIM_MODEL_ID = "SM_SCHEMA_DDL_DIM"
ENTITY_ID = "E_SCHEMA_DDL_FACT"
DIM_ENTITY_ID = "E_SCHEMA_DDL_DIM"
RELATION_ID = "J_SCHEMA_DDL_CUSTOMER"
METRIC_ID = "M_SCHEMA_DDL_AMOUNT"
REPORT_PATH = Path("reports/schema-change-ddl/latest.json")
HELD_REPORT_PATH = Path("reports/schema-change-ddl/held.json")

BASE_FACT_FIELDS = ["order_id", "customer_id", "event_date", "amount"]
DIM_FIELDS = ["customer_id", "customer_name"]


def _api(client: TestClient, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.request(method, path, json=payload)
    if response.status_code >= 400:
        raise AssertionError(
            f"{method} {path} failed with {response.status_code}: {response.text}"
        )
    return response.json()


def _drop_database(clickhouse: ClickHouseHttpClient) -> None:
    clickhouse.execute(f"DROP DATABASE IF EXISTS {DATABASE} SYNC")


def _create_database(clickhouse: ClickHouseHttpClient) -> None:
    _drop_database(clickhouse)
    clickhouse.execute(f"CREATE DATABASE {DATABASE}")
    clickhouse.execute(
        f"""
        CREATE TABLE {DATABASE}.fct_orders
        (
            order_id UInt64,
            customer_id UInt64,
            event_date Date,
            amount Decimal(18, 2)
        )
        ENGINE = MergeTree
        ORDER BY order_id
        """
    )
    clickhouse.execute(
        f"""
        CREATE TABLE {DATABASE}.dim_customer
        (
            customer_id UInt64,
            customer_name String
        )
        ENGINE = MergeTree
        ORDER BY customer_id
        """
    )
    clickhouse.execute(
        f"""
        INSERT INTO {DATABASE}.fct_orders VALUES
        (1, 101, '2026-01-01', 120.50),
        (2, 102, '2026-01-02', 80.00)
        """
    )
    clickhouse.execute(
        f"""
        INSERT INTO {DATABASE}.dim_customer VALUES
        (101, '客户甲'),
        (102, '客户乙')
        """
    )


def _cleanup_governance() -> None:
    with SessionLocal() as session:
        session.execute(
            delete(SchemaChangeEvent).where(SchemaChangeEvent.source_id == SOURCE_ID)
        )
        session.execute(delete(MetricVersion).where(MetricVersion.metric_id == METRIC_ID))
        session.execute(delete(Metric).where(Metric.id == METRIC_ID))
        session.execute(
            delete(SemanticJoinRelation).where(
                SemanticJoinRelation.id == RELATION_ID
            )
        )
        session.execute(
            delete(BusinessDomainTableBinding).where(
                BusinessDomainTableBinding.business_domain_id == DOMAIN_ID
            )
        )
        session.execute(
            delete(SemanticEntity).where(
                SemanticEntity.business_domain_id == DOMAIN_ID
            )
        )
        session.execute(
            delete(SemanticModel).where(
                SemanticModel.business_domain_id == DOMAIN_ID
            )
        )
        session.execute(delete(BusinessDomain).where(BusinessDomain.id == DOMAIN_ID))
        session.execute(delete(WarehouseSource).where(WarehouseSource.id == SOURCE_ID))
        session.commit()


def _scan(client: TestClient) -> dict[str, Any]:
    return _api(
        client,
        "POST",
        f"/api/chatbi/governance/sources/{SOURCE_ID}/scan",
        {"workspace_id": "demo", "operator_id": "metric_admin"},
    )


def _create_source_and_baseline_scan(client: TestClient) -> None:
    settings = get_settings()
    _api(
        client,
        "PUT",
        f"/api/chatbi/governance/sources/{SOURCE_ID}",
        {
            "workspace_id": "demo",
            "name": "Schema DDL Acceptance",
            "kind": "clickhouse",
            "connection": {
                "host": settings.clickhouse_host,
                "port": settings.clickhouse_http_port,
                "database": DATABASE,
                "username": settings.clickhouse_compiler_user,
                "credential_env": "CLICKHOUSE_COMPILER_PASSWORD",
            },
            "operator_id": "metric_admin",
        },
    )
    _scan(client)


def _asset(session, table_name: str) -> PhysicalTableAsset:
    asset = session.scalar(
        select(PhysicalTableAsset).where(
            PhysicalTableAsset.source_id == SOURCE_ID,
            PhysicalTableAsset.table_name == table_name,
        )
    )
    if asset is None:
        raise AssertionError(f"baseline scan did not create asset for {table_name}")
    return asset


def _create_governance_graph() -> None:
    with SessionLocal() as session:
        fact_asset = _asset(session, "fct_orders")
        dim_asset = _asset(session, "dim_customer")
        fact_contract = {
            str(item["name"]): str(item["type"]) for item in fact_asset.columns_json
        }
        dim_contract = {
            str(item["name"]): str(item["type"]) for item in dim_asset.columns_json
        }
        session.add(
            BusinessDomain(
                id=DOMAIN_ID,
                name="真实 DDL 验收域",
                description="仅用于隔离的结构变更验收。",
                owner="data-platform",
                business_goal="验证物理 DDL 变化的失败关闭和恢复。",
                status="ACTIVE",
            )
        )
        source = session.get(WarehouseSource, SOURCE_ID)
        source.business_domain_id = DOMAIN_ID
        session.add_all(
            [
                SemanticModel(
                    id=MODEL_ID,
                    business_domain_id=DOMAIN_ID,
                    name="订单事实",
                    warehouse="clickhouse",
                    physical_table=f"{DATABASE}.fct_orders",
                    default_time_field="event_date",
                    fields_json=BASE_FACT_FIELDS,
                    status="ACTIVE",
                ),
                SemanticModel(
                    id=DIM_MODEL_ID,
                    business_domain_id=DOMAIN_ID,
                    name="客户维度",
                    warehouse="clickhouse",
                    physical_table=f"{DATABASE}.dim_customer",
                    default_time_field="",
                    fields_json=DIM_FIELDS,
                    status="ACTIVE",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                SemanticEntity(
                    id=ENTITY_ID,
                    semantic_model_id=MODEL_ID,
                    business_domain_id=DOMAIN_ID,
                    name="订单事实",
                    grain="每行一笔订单",
                    primary_key_json=["order_id"],
                    entity_type="fact",
                    status="ACTIVE",
                ),
                SemanticEntity(
                    id=DIM_ENTITY_ID,
                    semantic_model_id=DIM_MODEL_ID,
                    business_domain_id=DOMAIN_ID,
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
                    id=BINDING_ID,
                    business_domain_id=DOMAIN_ID,
                    physical_asset_id=fact_asset.id,
                    semantic_model_id=MODEL_ID,
                    model_name="订单事实",
                    description="订单金额分析。",
                    entity_id=ENTITY_ID,
                    entity_name="订单事实",
                    entity_type="fact",
                    grain="每行一笔订单",
                    primary_keys_json=["order_id"],
                    default_time_field="event_date",
                    exposed_fields_json=BASE_FACT_FIELDS,
                    schema_contract_json=fact_contract,
                    status="PUBLISHED",
                    version=1,
                    created_by="metric_admin",
                ),
                BusinessDomainTableBinding(
                    id=DIM_BINDING_ID,
                    business_domain_id=DOMAIN_ID,
                    physical_asset_id=dim_asset.id,
                    semantic_model_id=DIM_MODEL_ID,
                    model_name="客户维度",
                    description="客户属性。",
                    entity_id=DIM_ENTITY_ID,
                    entity_name="客户维度",
                    entity_type="dimension",
                    grain="每行一个客户",
                    primary_keys_json=["customer_id"],
                    default_time_field="",
                    exposed_fields_json=DIM_FIELDS,
                    schema_contract_json=dim_contract,
                    status="PUBLISHED",
                    version=1,
                    created_by="metric_admin",
                ),
                SemanticJoinRelation(
                    id=RELATION_ID,
                    business_domain_id=DOMAIN_ID,
                    left_entity_id=ENTITY_ID,
                    right_entity_id=DIM_ENTITY_ID,
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
                    id=METRIC_ID,
                    business_domain_id=DOMAIN_ID,
                    name="真实 DDL 订单金额",
                    description="用于验证结构变化影响传播。",
                    metric_type="amount",
                    unit="CNY",
                    owner="data-platform",
                    status="PUBLISHED",
                ),
            ]
        )
        session.flush()
        session.add(
            MetricVersion(
                metric_id=METRIC_ID,
                version=1,
                semantic_model_id=MODEL_ID,
                expression_json={"op": "sum", "field": "amount"},
                default_aggregation="sum",
                time_dimension_id="D_DATE",
                status="PUBLISHED",
            )
        )
        session.commit()


def _snapshot() -> dict[str, Any]:
    with SessionLocal() as session:
        fact_asset = _asset(session, "fct_orders")
        events = session.scalars(
            select(SchemaChangeEvent)
            .where(SchemaChangeEvent.source_id == SOURCE_ID)
            .order_by(SchemaChangeEvent.detected_at, SchemaChangeEvent.id)
        ).all()
        return {
            "source": session.get(WarehouseSource, SOURCE_ID).status,
            "domain": session.get(BusinessDomain, DOMAIN_ID).status,
            "asset": fact_asset.status,
            "binding": session.get(
                BusinessDomainTableBinding, BINDING_ID
            ).status,
            "model": session.get(SemanticModel, MODEL_ID).status,
            "entity": session.get(SemanticEntity, ENTITY_ID).status,
            "relation": session.get(SemanticJoinRelation, RELATION_ID).status,
            "metric": session.get(Metric, METRIC_ID).status,
            "events": [
                {
                    "type": event.change_type,
                    "severity": event.severity,
                    "status": event.status,
                    "diff": event.diff_json,
                }
                for event in events
            ],
        }


def _assert_blocked(snapshot: dict[str, Any], asset_status: str) -> None:
    expected = {
        "source": "DEGRADED",
        "domain": "DEGRADED",
        "asset": asset_status,
        "binding": "IMPACTED",
        "model": "DEGRADED",
        "entity": "DEGRADED",
        "relation": "BLOCKED",
        "metric": "BLOCKED",
    }
    for key, value in expected.items():
        if snapshot[key] != value:
            raise AssertionError(f"{key}: expected {value}, got {snapshot[key]}")


def _assert_recovered(snapshot: dict[str, Any]) -> None:
    expected = {
        "source": "SCANNED",
        "domain": "ACTIVE",
        "asset": "ACTIVE",
        "binding": "PUBLISHED",
        "model": "ACTIVE",
        "entity": "ACTIVE",
        "relation": "PUBLISHED",
        "metric": "PUBLISHED",
    }
    for key, value in expected.items():
        if snapshot[key] != value:
            raise AssertionError(f"{key}: expected {value}, got {snapshot[key]}")
    if any(event["status"] == "OPEN" for event in snapshot["events"]):
        raise AssertionError("recovery left an OPEN schema change event")


def _review_and_publish_model(
    client: TestClient,
    *,
    fields: list[str],
    description: str,
) -> None:
    _api(
        client,
        "PUT",
        f"/api/chatbi/governance/domains/{DOMAIN_ID}/models/{BINDING_ID}",
        {
            "workspace_id": "demo",
            "model_name": "订单事实",
            "description": description,
            "entity_type": "fact",
            "grain": "每行一笔订单",
            "primary_keys": ["order_id"],
            "default_time_field": "event_date",
            "exposed_fields": fields,
            "operator_id": "metric_admin",
        },
    )
    _api(
        client,
        "POST",
        f"/api/chatbi/governance/domains/{DOMAIN_ID}/models/{BINDING_ID}/publish",
        {"workspace_id": "demo", "operator_id": "metric_admin"},
    )


def _record_phase(
    phases: list[dict[str, Any]],
    scenario: str,
    phase: str,
    snapshot: dict[str, Any],
) -> None:
    phases.append({"scenario": scenario, "phase": phase, "snapshot": snapshot})


def hold_broken_state(scenario: str) -> dict[str, Any]:
    settings = get_settings()
    clickhouse = ClickHouseHttpClient(
        host=settings.clickhouse_host,
        port=settings.clickhouse_http_port,
        user=settings.clickhouse_compiler_user,
        password=settings.clickhouse_compiler_password,
    )
    _cleanup_governance()
    _create_database(clickhouse)
    try:
        with TestClient(app) as client:
            _create_source_and_baseline_scan(client)
            _create_governance_graph()
            baseline = _snapshot()
            _assert_recovered(baseline)

            if scenario == "drop_table":
                clickhouse.execute(f"DROP TABLE {DATABASE}.fct_orders SYNC")
                expected_event = "TABLE_REMOVED"
                expected_asset = "MISSING"
            elif scenario == "drop_column":
                clickhouse.execute(
                    f"ALTER TABLE {DATABASE}.fct_orders DROP COLUMN amount"
                )
                expected_event = "BREAKING_COLUMNS"
                expected_asset = "CHANGED"
            elif scenario == "modify_type":
                clickhouse.execute(
                    f"""
                    ALTER TABLE {DATABASE}.fct_orders
                    MODIFY COLUMN amount Float64
                    """
                )
                expected_event = "BREAKING_COLUMNS"
                expected_asset = "CHANGED"
            else:
                raise ValueError(f"unsupported hold scenario: {scenario}")

            _scan(client)
            blocked = _snapshot()
            _assert_blocked(blocked, expected_asset)
            open_events = [
                event for event in blocked["events"] if event["status"] == "OPEN"
            ]
            if not open_events or open_events[-1]["type"] != expected_event:
                raise AssertionError(
                    f"{scenario} did not create expected {expected_event} event"
                )
            if scenario == "drop_column" and "amount" not in open_events[-1][
                "diff"
            ]["removed_columns"]:
                raise AssertionError("held DROP COLUMN did not remove amount")
            return {
                "status": "HELD_BLOCKED",
                "scenario": scenario,
                "database": DATABASE,
                "source_id": SOURCE_ID,
                "domain_id": DOMAIN_ID,
                "held_at": datetime.now(UTC).isoformat(),
                "baseline": baseline,
                "blocked": blocked,
                "cleanup_performed": False,
                "recovery_command": (
                    ".venv/bin/python -m scripts.evaluate_schema_change_ddl "
                    "--recover-held"
                ),
            }
    except Exception:
        _cleanup_governance()
        _drop_database(clickhouse)
        raise


def recover_held_state(report_path: Path = HELD_REPORT_PATH) -> dict[str, Any]:
    if not report_path.exists():
        raise FileNotFoundError(f"held-state report does not exist: {report_path}")
    held = json.loads(report_path.read_text(encoding="utf-8"))
    if held.get("status") != "HELD_BLOCKED":
        raise ValueError("held-state report is not waiting for recovery")
    scenario = str(held.get("scenario", ""))
    settings = get_settings()
    clickhouse = ClickHouseHttpClient(
        host=settings.clickhouse_host,
        port=settings.clickhouse_http_port,
        user=settings.clickhouse_compiler_user,
        password=settings.clickhouse_compiler_password,
    )
    with TestClient(app) as client:
        if scenario == "drop_table":
            clickhouse.execute(
                f"""
                CREATE TABLE {DATABASE}.fct_orders
                (
                    order_id UInt64,
                    customer_id UInt64,
                    event_date Date,
                    amount Decimal(18, 2)
                )
                ENGINE = MergeTree
                ORDER BY order_id
                """
            )
        elif scenario == "drop_column":
            clickhouse.execute(
                f"""
                ALTER TABLE {DATABASE}.fct_orders
                ADD COLUMN amount Decimal(18, 2) DEFAULT 0
                """
            )
        elif scenario != "modify_type":
            raise ValueError(f"unsupported held scenario: {scenario}")
        _scan(client)
        _review_and_publish_model(
            client,
            fields=BASE_FACT_FIELDS,
            description=f"真实 DDL {scenario} 事故恢复后人工复核。",
        )
        recovered = _snapshot()
        _assert_recovered(recovered)

    _cleanup_governance()
    _drop_database(clickhouse)
    cleanup = verify_cleanup()
    result = {
        **held,
        "status": "RECOVERED",
        "recovered_at": datetime.now(UTC).isoformat(),
        "recovered": recovered,
        "cleanup_performed": True,
        "cleanup": cleanup,
    }
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def run_acceptance() -> dict[str, Any]:
    settings = get_settings()
    clickhouse = ClickHouseHttpClient(
        host=settings.clickhouse_host,
        port=settings.clickhouse_http_port,
        user=settings.clickhouse_compiler_user,
        password=settings.clickhouse_compiler_password,
    )
    phases: list[dict[str, Any]] = []
    cleanup = {"postgres": False, "clickhouse": False}
    started_at = datetime.now(UTC)
    _cleanup_governance()
    _create_database(clickhouse)
    try:
        with TestClient(app) as client:
            _create_source_and_baseline_scan(client)
            _create_governance_graph()
            baseline = _snapshot()
            _assert_recovered(baseline)
            _record_phase(phases, "baseline", "healthy", baseline)

            clickhouse.execute(f"DROP TABLE {DATABASE}.fct_orders SYNC")
            _scan(client)
            blocked = _snapshot()
            _assert_blocked(blocked, "MISSING")
            if blocked["events"][-1]["type"] != "TABLE_REMOVED":
                raise AssertionError("DROP TABLE did not produce TABLE_REMOVED")
            _record_phase(phases, "drop_table", "blocked", blocked)

            clickhouse.execute(
                f"""
                CREATE TABLE {DATABASE}.fct_orders
                (
                    order_id UInt64,
                    customer_id UInt64,
                    event_date Date,
                    amount Decimal(18, 2)
                )
                ENGINE = MergeTree
                ORDER BY order_id
                """
            )
            _scan(client)
            _review_and_publish_model(
                client,
                fields=BASE_FACT_FIELDS,
                description="物理表恢复后人工复核。",
            )
            recovered = _snapshot()
            _assert_recovered(recovered)
            _record_phase(phases, "drop_table", "recovered", recovered)

            clickhouse.execute(
                f"ALTER TABLE {DATABASE}.fct_orders DROP COLUMN amount"
            )
            _scan(client)
            blocked = _snapshot()
            _assert_blocked(blocked, "CHANGED")
            last_open = [event for event in blocked["events"] if event["status"] == "OPEN"][-1]
            if (
                last_open["type"] != "BREAKING_COLUMNS"
                or "amount" not in last_open["diff"]["removed_columns"]
            ):
                raise AssertionError("DROP COLUMN did not record amount as removed")
            _record_phase(phases, "drop_column", "blocked", blocked)

            clickhouse.execute(
                f"""
                ALTER TABLE {DATABASE}.fct_orders
                ADD COLUMN amount Decimal(18, 2) DEFAULT 0
                """
            )
            _scan(client)
            _review_and_publish_model(
                client,
                fields=BASE_FACT_FIELDS,
                description="amount 字段恢复后人工复核。",
            )
            recovered = _snapshot()
            _assert_recovered(recovered)
            _record_phase(phases, "drop_column", "recovered", recovered)

            clickhouse.execute(
                f"""
                ALTER TABLE {DATABASE}.fct_orders
                MODIFY COLUMN amount Float64
                """
            )
            _scan(client)
            blocked = _snapshot()
            _assert_blocked(blocked, "CHANGED")
            last_open = [event for event in blocked["events"] if event["status"] == "OPEN"][-1]
            type_changes = last_open["diff"]["type_changes"]
            if (
                last_open["type"] != "BREAKING_COLUMNS"
                or not type_changes
                or type_changes[0]["field"] != "amount"
                or type_changes[0]["new_type"] != "Float64"
            ):
                raise AssertionError("MODIFY COLUMN did not record the type transition")
            _record_phase(phases, "modify_type", "blocked", blocked)

            _review_and_publish_model(
                client,
                fields=BASE_FACT_FIELDS,
                description="确认 amount 已从 Decimal(18,2) 调整为 Float64。",
            )
            recovered = _snapshot()
            _assert_recovered(recovered)
            _record_phase(phases, "modify_type", "recovered", recovered)

            impact_response = client.get(
                "/api/chatbi/governance/schema-impacts",
                params={"workspace_id": "demo", "event_status": "ALL"},
            )
            impact_response.raise_for_status()
            impact_items = [
                item
                for item in impact_response.json()["items"]
                if item["source_id"] == SOURCE_ID
            ]
            if not impact_items or any(item["status"] == "OPEN" for item in impact_items):
                raise AssertionError("impact API did not expose a fully resolved event history")

        return {
            "status": "PASS",
            "database": DATABASE,
            "source_id": SOURCE_ID,
            "domain_id": DOMAIN_ID,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "scenarios": ["DROP_TABLE", "DROP_COLUMN", "MODIFY_COLUMN_TYPE"],
            "phase_count": len(phases),
            "phases": phases,
        }
    finally:
        try:
            _cleanup_governance()
            cleanup["postgres"] = True
        finally:
            _drop_database(clickhouse)
            cleanup["clickhouse"] = True


def verify_cleanup() -> dict[str, Any]:
    settings = get_settings()
    clickhouse = ClickHouseHttpClient(
        host=settings.clickhouse_host,
        port=settings.clickhouse_http_port,
        user=settings.clickhouse_compiler_user,
        password=settings.clickhouse_compiler_password,
    )
    database_count = int(
        clickhouse.execute(
            "SELECT count() FROM system.databases "
            f"WHERE name = '{DATABASE}'"
        ).strip()
        or 0
    )
    with SessionLocal() as session:
        postgres_counts = {
            "source": int(session.get(WarehouseSource, SOURCE_ID) is not None),
            "domain": int(session.get(BusinessDomain, DOMAIN_ID) is not None),
            "metric": int(session.get(Metric, METRIC_ID) is not None),
            "schema_events": len(
                session.scalars(
                    select(SchemaChangeEvent).where(
                        SchemaChangeEvent.source_id == SOURCE_ID
                    )
                ).all()
            ),
        }
    result = {
        "clickhouse_database_count": database_count,
        "postgres_counts": postgres_counts,
        "verified": database_count == 0 and not any(postgres_counts.values()),
    }
    if not result["verified"]:
        raise AssertionError(f"isolated acceptance resources were not cleaned: {result}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument(
        "--hold-after",
        choices=["drop_table", "drop_column", "modify_type"],
        help="create one real breaking change and keep it blocked for UI inspection",
    )
    parser.add_argument(
        "--recover-held",
        action="store_true",
        help="recover and clean the state stored in reports/schema-change-ddl/held.json",
    )
    args = parser.parse_args()
    if args.hold_after and args.recover_held:
        parser.error("--hold-after and --recover-held cannot be used together")
    output_path = HELD_REPORT_PATH if args.hold_after or args.recover_held else args.report
    report: dict[str, Any]
    try:
        if args.hold_after:
            report = hold_broken_state(args.hold_after)
        elif args.recover_held:
            report = recover_held_state()
        else:
            report = run_acceptance()
            report["cleanup"] = verify_cleanup()
    except Exception as error:
        report = {
            "status": "FAIL",
            "database": DATABASE,
            "completed_at": datetime.now(UTC).isoformat(),
            "error": f"{type(error).__name__}: {error}",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.hold_after:
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "scenario": report["scenario"],
                    "database": report["database"],
                    "source_id": report["source_id"],
                    "domain_id": report["domain_id"],
                    "report": str(output_path),
                    "cleanup_performed": False,
                    "recovery_command": report["recovery_command"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.recover_held:
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "scenario": report["scenario"],
                    "report": str(output_path),
                    "cleanup": report["cleanup"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(
        json.dumps(
            {
                "status": report["status"],
                "database": report["database"],
                "scenarios": report["scenarios"],
                "phase_count": report["phase_count"],
                "report": str(output_path),
                "cleanup": report["cleanup"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
