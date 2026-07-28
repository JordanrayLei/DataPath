"""Rebuild production_benchmark through the same public APIs used by the frontend.

Inputs are canonical schema and business definitions only. Evaluation datasets,
Bad Cases, prior reports, and runtime logs are never opened by this script.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.production_benchmark_semantics import (
    DEFAULT_TIME_FIELDS,
    ENTITY_KEYS,
    FACT_MODEL_IDS,
    METRIC_DESCRIPTIONS,
    MODEL_FIELDS,
    MODEL_NAMES,
    MODEL_TABLES,
    PUBLISHED_METRICS,
    RELATIONS,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_CONTRACT = ROOT / "data" / "evaluation" / "production" / "schema_contract.json"
CROSS_FACT = ROOT / "data" / "semantic_bootstrap" / "production_cross_fact_preheat_v1.json"
OUT = ROOT / "reports" / "zero-to-one" / "human-governance-publication.json"


def require_ok(response, action: str) -> dict:
    if not response.is_success:
        raise RuntimeError(f"{action} failed: HTTP {response.status_code} {response.text}")
    return response.json()


def schema_grains() -> dict[str, str]:
    contract = json.loads(SCHEMA_CONTRACT.read_text(encoding="utf-8"))
    return {item["name"]: item["grain"] for item in contract["tables"]}


def table_payloads() -> list[dict]:
    grains = schema_grains()
    result = []
    for model_id, physical_table in MODEL_TABLES.items():
        table = physical_table.split(".", 1)[1]
        default_time = DEFAULT_TIME_FIELDS[model_id] or "business_date"
        result.append(
            {
                "table": table,
                "enabled": True,
                "semantic_model_id": model_id,
                "model_name": MODEL_NAMES[model_id],
                "entity_id": model_id.replace("SM_", "E_", 1),
                "entity_name": MODEL_NAMES[model_id],
                "entity_type": "fact" if model_id in FACT_MODEL_IDS else "dimension",
                "grain": grains[table],
                "primary_keys": ENTITY_KEYS[model_id],
                "default_time_field": default_time,
            }
        )
    return result


def mappings(model_ids: list[str], field: str, *, grain: str | None = None) -> list[dict]:
    return [
        {
            "semantic_model_id": model_id,
            "field": field,
            "kind": "time_grain" if grain else "field",
            **({"grain": grain} if grain else {}),
        }
        for model_id in model_ids
        if field in MODEL_FIELDS[model_id]
    ]


def dimension_payloads() -> list[dict]:
    facts = sorted(FACT_MODEL_IDS)
    common = ["eq", "neq", "in", "not_in", "between"]
    return [
        {"dimension_id": "D_DATE", "name": "日期", "dimension_type": "time_grain", "allowed_operators": common, "mappings": mappings(facts, "business_date", grain="day")},
        {"dimension_id": "D_MONTH", "name": "月份", "dimension_type": "time_grain", "allowed_operators": common, "mappings": mappings(facts, "business_date", grain="month")},
        {"dimension_id": "D_PROD_REGION", "name": "业务区域", "dimension_type": "enum", "allowed_operators": common, "mappings": mappings(facts, "region_code")},
        {"dimension_id": "D_PROD_STATUS", "name": "业务状态", "dimension_type": "enum", "allowed_operators": common, "mappings": mappings(facts, "status_code")},
        {"dimension_id": "D_PROD_CURRENCY", "name": "币种", "dimension_type": "enum", "allowed_operators": common, "mappings": mappings(facts, "currency_code")},
        {"dimension_id": "D_PROD_WAREHOUSE", "name": "仓库", "dimension_type": "enum", "allowed_operators": ["eq", "neq", "in", "not_in"], "mappings": [{"semantic_model_id": "SM_PROD_SHIPMENTS", "source_model_id": "SM_PROD_WAREHOUSE", "field": "warehouse_id", "kind": "field"}]},
        {"dimension_id": "D_PROD_PARENT_ORDER_STATUS", "name": "关联订单状态", "dimension_type": "enum", "allowed_operators": common, "mappings": [{"semantic_model_id": model, "source_model_id": "SM_PROD_ORDERS", "field": "status_code", "kind": "field"} for model in ["SM_PROD_ORDER_ITEMS", "SM_PROD_PAYMENTS", "SM_PROD_SHIPMENTS", "SM_PROD_SERVICE_TICKETS"]]},
        {"dimension_id": "D_PROD_PARENT_ORDER_REGION", "name": "关联订单区域", "dimension_type": "enum", "allowed_operators": common, "mappings": [{"semantic_model_id": model, "source_model_id": "SM_PROD_ORDERS", "field": "region_code", "kind": "field"} for model in ["SM_PROD_ORDER_ITEMS", "SM_PROD_PAYMENTS", "SM_PROD_SHIPMENTS", "SM_PROD_SERVICE_TICKETS"]]},
        {"dimension_id": "D_PROD_PARENT_ORDER_CURRENCY", "name": "关联订单币种", "dimension_type": "enum", "allowed_operators": common, "mappings": [{"semantic_model_id": model, "source_model_id": "SM_PROD_ORDERS", "field": "currency_code", "kind": "field"} for model in ["SM_PROD_ORDER_ITEMS", "SM_PROD_PAYMENTS", "SM_PROD_SHIPMENTS", "SM_PROD_SERVICE_TICKETS"]]},
        {"dimension_id": "D_PROD_PARENT_PAYMENT_STATUS", "name": "关联支付状态", "dimension_type": "enum", "allowed_operators": common, "mappings": [{"semantic_model_id": "SM_PROD_REFUNDS", "source_model_id": "SM_PROD_PAYMENTS", "field": "status_code", "kind": "field"}]},
    ]


def metric_dimensions(metric_id: str, model_id: str) -> list[str]:
    result = ["D_DATE", "D_MONTH"]
    for dimension_id, field in (
        ("D_PROD_REGION", "region_code"),
        ("D_PROD_STATUS", "status_code"),
        ("D_PROD_CURRENCY", "currency_code"),
    ):
        if field in MODEL_FIELDS[model_id]:
            result.append(dimension_id)
    if metric_id == "M_PROD_SHIPMENT_COUNT":
        result.append("D_PROD_WAREHOUSE")
    joined = {
        "M_PROD_ITEM_NET_REVENUE": ["D_PROD_PARENT_ORDER_STATUS", "D_PROD_PARENT_ORDER_REGION", "D_PROD_PARENT_ORDER_CURRENCY"],
        "M_PROD_PAYMENT_AMOUNT": ["D_PROD_PARENT_ORDER_STATUS", "D_PROD_PARENT_ORDER_REGION", "D_PROD_PARENT_ORDER_CURRENCY"],
        "M_PROD_SHIPMENT_COUNT": ["D_PROD_PARENT_ORDER_STATUS", "D_PROD_PARENT_ORDER_REGION", "D_PROD_PARENT_ORDER_CURRENCY"],
        "M_PROD_SERVICE_TICKET_COUNT": ["D_PROD_PARENT_ORDER_STATUS", "D_PROD_PARENT_ORDER_REGION", "D_PROD_PARENT_ORDER_CURRENCY"],
        "M_PROD_REFUND_AMOUNT": ["D_PROD_PARENT_PAYMENT_STATUS"],
    }
    return list(dict.fromkeys(result + joined.get(metric_id, [])))


def main() -> int:
    records: dict[str, object] = {"source": {}, "joins": [], "metrics": []}
    with TestClient(app) as client:
        source_id = "production_warehouse"
        source = require_ok(
            client.put(
                f"/api/chatbi/governance/sources/{source_id}",
                json={
                    "workspace_id": "demo",
                    "name": "生产分析仓库",
                    "kind": "clickhouse",
                    "operator_id": "simulated_metric_admin",
                    "connection": {"host": "127.0.0.1", "port": 8123, "database": "production_benchmark", "username": "chatbi_reader", "credential_env": "CLICKHOUSE_READER_PASSWORD"},
                },
            ),
            "save warehouse source",
        )["source"]
        scanned = require_ok(
            client.post(f"/api/chatbi/governance/sources/{source_id}/scan", json={"workspace_id": "demo", "operator_id": "simulated_metric_admin"}),
            "scan warehouse source",
        )["source"]
        confirmed = require_ok(
            client.put(
                f"/api/chatbi/governance/sources/{source_id}/confirmation",
                json={
                    "workspace_id": "demo",
                    "business_domain_id": "production_benchmark",
                    "business_domain_name": "全渠道零售运营",
                    "business_domain_description": "覆盖订单、商品、支付、退款、履约、库存、客服和营销的多事实业务域",
                    "tables": table_payloads(),
                    "dimensions": dimension_payloads(),
                    "operator_id": "simulated_metric_admin",
                },
            ),
            "confirm warehouse governance",
        )["source"]
        published_source = require_ok(
            client.post(f"/api/chatbi/governance/sources/{source_id}/publish", json={"workspace_id": "demo", "operator_id": "simulated_metric_admin"}),
            "publish warehouse governance",
        )["source"]
        records["source"] = {
            "transport": "public API used by frontend",
            "scan_table_count": scanned["scan_snapshot"]["table_count"],
            "scan_column_count": scanned["scan_snapshot"]["column_count"],
            "schema_sha256": scanned["scan_snapshot"]["schema_sha256"],
            "confirmed_models": len(confirmed["governance"]["tables"]),
            "confirmed_dimensions": len(confirmed["governance"]["dimensions"]),
            "status": published_source["status"],
        }

        for relation_id, (left, right, left_keys, right_keys, relationship, strategy, relation_status) in RELATIONS.items():
            if relation_status != "PUBLISHED" or strategy != "safe":
                continue
            body = {"workspace_id": "demo", "left_entity_id": left.replace("SM_", "E_", 1), "right_entity_id": right.replace("SM_", "E_", 1), "left_keys": left_keys, "right_keys": right_keys, "relationship_type": relationship, "join_type": "left", "fanout_strategy": strategy, "priority": 20}
            require_ok(client.put(f"/api/chatbi/join-graph/drafts/{relation_id}", json=body), f"save {relation_id}")
            validation = require_ok(client.post(f"/api/chatbi/join-graph/drafts/{relation_id}/validate"), f"validate {relation_id}")
            publication = require_ok(client.post(f"/api/chatbi/join-graph/drafts/{relation_id}/publish"), f"publish {relation_id}")
            records["joins"].append({"relation_id": relation_id, "validation": validation["validation"], "version": publication["version"]})

        for metric_id, name, model_id, metric_type, unit, expression, _ in PUBLISHED_METRICS:
            payload = {"workspace_id": "demo", "metric_id": metric_id, "business_domain_id": "production_benchmark", "name": name, "description": METRIC_DESCRIPTIONS[metric_id], "metric_type": metric_type, "unit": unit, "owner": "data-platform", "aliases": [], "positive_examples": [], "negative_examples": [], "semantic_model_id": model_id, "expression": expression, "default_aggregation": "default", "time_dimension_id": "D_DATE", "dimension_ids": metric_dimensions(metric_id, model_id)}
            saved = require_ok(client.put(f"/api/chatbi/metrics/manage/drafts/{metric_id}", json=payload), f"save {metric_id}")
            published = require_ok(client.post(f"/api/chatbi/metrics/manage/drafts/{metric_id}/publish", json={"workspace_id": "demo"}), f"publish {metric_id}")
            records["metrics"].append({"metric_id": metric_id, "kind": "single_fact", "version": published["version"], "validation": saved["draft"]["validation"]})

        cross_package = json.loads(CROSS_FACT.read_text(encoding="utf-8"))
        for metric_id, spec in cross_package["metrics"].items():
            payload = {"workspace_id": "demo", "metric_id": metric_id, "business_domain_id": "production_benchmark", "name": spec["canonical_name"], "description": spec["description"], "metric_type": spec["metric_type"], "unit": spec["unit"], "owner": spec["owner"], "aliases": [], "positive_examples": [], "negative_examples": [], "semantic_model_id": spec["semantic_model_id"], "expression": spec["expression"], "default_aggregation": spec["default_aggregation"], "time_dimension_id": spec["time_dimension_id"], "dimension_ids": spec["dimension_ids"]}
            saved = require_ok(client.put(f"/api/chatbi/metrics/manage/drafts/{metric_id}", json=payload), f"save {metric_id}")
            published = require_ok(client.post(f"/api/chatbi/metrics/manage/drafts/{metric_id}/publish", json={"workspace_id": "demo"}), f"publish {metric_id}")
            records["metrics"].append({"metric_id": metric_id, "kind": "cross_fact", "version": published["version"], "validation": saved["draft"]["validation"]})

    report = {
        "publication_id": "zero-to-one-human-governance-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "operator": "simulated_metric_admin",
        "forbidden_inputs_opened": [],
        "allowed_inputs": [str(SCHEMA_CONTRACT.relative_to(ROOT)), "canonical production semantic constants", str(CROSS_FACT.relative_to(ROOT))],
        "schema_contract_sha256": hashlib.sha256(SCHEMA_CONTRACT.read_bytes()).hexdigest(),
        "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source": records["source"], "join_count": len(records["joins"]), "metric_count": len(records["metrics"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
