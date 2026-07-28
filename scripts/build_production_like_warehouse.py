"""Build a deterministic production-like ClickHouse warehouse from the contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.clickhouse_http import ClickHouseHttpClient, split_sql_statements


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data" / "evaluation" / "production" / "schema_contract.json"
DDL_PATH = ROOT / "infra" / "clickhouse" / "sql" / "40-production-like-warehouse.sql"
SNAPSHOT_PATH = ROOT / "data" / "evaluation" / "production" / "production_snapshot.json"
DATABASE = "production_benchmark"
READER_USER = "chatbi_reader"
PROFILE_SCALE = {"smoke": 1_000, "standard": 100_000, "production": 500_000}

FACT_WEIGHTS = {
    "fct_orders": 1.0,
    "fct_order_items": 3.0,
    "fct_payments": 1.2,
    "fct_refunds": 0.15,
    "fct_shipments": 1.5,
    "fct_inventory_snapshot": 2.0,
    "fct_service_tickets": 0.2,
    "fct_marketing_touch": 2.0,
}

RELATION_KEYS = {
    "fct_orders": ["order_id", "customer_sk", "tenant_id", "order_date", "purchase_ts"],
    "fct_order_items": ["order_item_id", "order_id", "product_sk", "seller_sk", "tenant_id"],
    "fct_payments": ["payment_id", "order_id", "customer_sk", "tenant_id", "payment_ts"],
    "fct_refunds": ["refund_id", "payment_id", "order_id", "tenant_id", "refund_ts"],
    "fct_shipments": ["shipment_id", "order_id", "warehouse_sk", "carrier_sk", "tenant_id"],
    "fct_inventory_snapshot": ["snapshot_id", "product_sk", "warehouse_sk", "tenant_id", "snapshot_date"],
    "fct_service_tickets": ["ticket_id", "order_id", "customer_sk", "employee_sk", "tenant_id"],
    "fct_marketing_touch": ["touch_id", "customer_sk", "campaign_sk", "channel_sk", "tenant_id"],
    "bridge_order_promotion": ["order_id", "promotion_sk", "tenant_id"],
    "bridge_product_category": ["product_sk", "category_sk", "valid_from", "valid_to"],
    "bridge_customer_segment": ["customer_sk", "segment_sk", "valid_from", "valid_to"],
    "bridge_shipment_item": ["shipment_id", "order_item_id", "tenant_id"],
}

RELATION_INTEGRITY_CHECKS = {
    "order_items_to_orders": ("fct_order_items", "fct_orders", "order_id"),
    "payments_to_orders": ("fct_payments", "fct_orders", "order_id"),
    "refunds_to_payments": ("fct_refunds", "fct_payments", "payment_id"),
    "shipments_to_orders": ("fct_shipments", "fct_orders", "order_id"),
    "shipments_to_warehouses": ("fct_shipments", "dim_warehouse", "warehouse_sk"),
    "inventory_to_products": ("fct_inventory_snapshot", "dim_product_scd2", "product_sk"),
    "inventory_to_warehouses": ("fct_inventory_snapshot", "dim_warehouse", "warehouse_sk"),
    "service_tickets_to_orders": ("fct_service_tickets", "fct_orders", "order_id"),
    "marketing_touches_to_customers": ("fct_marketing_touch", "dim_customer_scd2", "customer_sk"),
}


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _column_type(name: str) -> str:
    if name.endswith("_date") or name in {"valid_from", "valid_to", "order_date", "snapshot_date"}:
        return "Date"
    if name.endswith("_ts") or name == "ingested_at":
        return "DateTime64(3)"
    if name.endswith("_id") or name.endswith("_sk"):
        return "UInt64"
    if name == "quantity":
        return "UInt32"
    if any(token in name for token in ("amount", "value", "price", "cost", "rate")):
        return "Float64"
    if name.startswith("is_"):
        return "UInt8"
    return "LowCardinality(String)"


def table_columns(table: dict[str, Any]) -> list[tuple[str, str]]:
    name = table["name"]
    kind = table["kind"]
    keys = list(RELATION_KEYS.get(name, []))
    if not keys:
        if kind == "dimension":
            stem = name.removeprefix("dim_").removesuffix("_scd2")
            keys = [f"{stem}_sk", f"{stem}_id", "tenant_id"]
            if name.endswith("_scd2"):
                keys += ["valid_from", "valid_to", "is_current"]
        elif kind == "aggregate":
            keys = ["tenant_id", "period_date", "metric_value"]
        elif kind == "decoy":
            keys = ["record_id", "tenant_id", "amount"]
        else:
            keys = ["record_id", "tenant_id"]
    semantic = [
        "business_date", "event_ts", "currency_code", "status_code", "quantity",
        "gross_amount", "discount_amount", "net_amount", "region_code", "timezone",
        "source_system", "source_version", "is_deleted", "ingested_at",
    ]
    names = []
    for candidate in keys + semantic:
        if candidate not in names:
            names.append(candidate)
        if len(names) == int(table["column_count"]):
            break
    while len(names) < int(table["column_count"]):
        names.append(f"descriptive_attribute_{len(names) + 1:02d}")
    return [(column, _column_type(column)) for column in names]


def render_ddl(contract: dict[str, Any]) -> str:
    statements = [f"CREATE DATABASE IF NOT EXISTS {DATABASE}"]
    for table in contract["tables"]:
        columns = ",\n    ".join(f"`{name}` {type_name}" for name, type_name in table_columns(table))
        order_keys = [name for name, _ in table_columns(table) if name.endswith("_id") or name.endswith("_sk")][:3]
        order_by = ", ".join(f"`{name}`" for name in order_keys) or "tuple()"
        statements.append(
            f"CREATE TABLE IF NOT EXISTS {DATABASE}.`{table['name']}` (\n    {columns}\n) "
            f"ENGINE = MergeTree ORDER BY ({order_by})"
        )
    return ";\n\n".join(statements) + ";\n"


def grant_reader_access(client: ClickHouseHttpClient) -> None:
    client.execute(f"GRANT SELECT ON {DATABASE}.* TO {READER_USER}")


def _row_count(table: dict[str, Any], scale: int) -> int:
    name, kind = table["name"], table["kind"]
    if kind == "fact":
        return max(1, int(scale * FACT_WEIGHTS[name]))
    if kind == "bridge":
        return max(1, int(scale * 0.6))
    if kind == "aggregate":
        return max(1, int(scale * 0.05))
    if kind == "decoy":
        return max(100, int(scale * 0.01))
    return max(100, min(50_000, int(scale * 0.1)))


def _expression(name: str, type_name: str) -> str:
    if type_name == "UInt64":
        salt = int(hashlib.sha256(name.encode()).hexdigest()[:4], 16)
        key_cardinalities = {
            "order_id": 500_000,
            "order_item_id": 1_500_000,
            "payment_id": 600_000,
            "refund_id": 75_000,
            "shipment_id": 750_000,
            "snapshot_id": 1_000_000,
            "ticket_id": 100_000,
            "touch_id": 1_000_000,
            "customer_sk": 50_000,
            "product_sk": 50_000,
            "seller_sk": 50_000,
            "warehouse_sk": 50_000,
            "carrier_sk": 50_000,
            "employee_sk": 50_000,
            "campaign_sk": 50_000,
            "channel_sk": 50_000,
            "promotion_sk": 50_000,
            "category_sk": 50_000,
            "segment_sk": 50_000,
            "tenant_id": 50_000,
        }
        cardinality = key_cardinalities.get(name, 1_000_000)
        return f"toUInt64((number + {salt}) % {cardinality} + 1)"
    if type_name == "UInt8":
        return "toUInt8(number % 2)"
    if type_name == "UInt32":
        return "toUInt32(number % 100 + 1)"
    if type_name == "Date":
        if name == "valid_to":
            return "toDate('2024-01-01') + toIntervalDay((number * 2654435761) % 730)"
        return "toDate('2023-01-01') + toIntervalDay((number * 2654435761) % 730)"
    if type_name == "DateTime64(3)":
        return "toDateTime64('2023-01-01 00:00:00', 3) + toIntervalSecond((number * 2654435761) % 63072000)"
    if type_name == "Float64":
        return "round(toFloat64((number * 2654435761) % 1000000) / 100.0, 2)"
    categorical_values = {
        "currency_code": ("CNY", "USD", "EUR", "JPY", "GBP"),
        "status_code": ("created", "paid", "processing", "shipped", "completed", "cancelled", "refunded"),
        "region_code": ("north", "northeast", "east", "central", "south", "southwest", "northwest"),
        "timezone": ("Asia/Shanghai", "Asia/Tokyo", "Europe/London", "America/New_York"),
        "source_system": ("erp", "crm", "oms", "wms", "payment", "marketing"),
        "source_version": ("v1", "v2", "v3"),
    }
    if name in categorical_values:
        values = ", ".join(f"'{value}'" for value in categorical_values[name])
        return f"arrayElement([{values}], toUInt32(number % {len(categorical_values[name])} + 1))"
    return f"concat('{name}_', toString(number % 1000))"


def insert_sql(table: dict[str, Any], rows: int) -> str:
    columns = table_columns(table)
    names = ", ".join(f"`{name}`" for name, _ in columns)
    values = ", ".join(_expression(name, type_name) for name, type_name in columns)
    return f"INSERT INTO {DATABASE}.`{table['name']}` ({names}) SELECT {values} FROM numbers({rows})"


def relation_integrity_sql(child: str, parent: str, key: str) -> str:
    return (
        f"SELECT count() FROM {DATABASE}.`{child}` AS child "
        f"LEFT ANTI JOIN {DATABASE}.`{parent}` AS parent "
        f"ON child.`{key}` = parent.`{key}`"
    )


def validate_ddl(contract: dict[str, Any], ddl: str) -> dict[str, Any]:
    expected = {table["name"] for table in contract["tables"]}
    present = {name for name in expected if f"{DATABASE}.`{name}`" in ddl}
    column_total = sum(len(table_columns(table)) for table in contract["tables"])
    return {
        "table_count": len(present),
        "expected_table_count": len(expected),
        "column_count": column_total,
        "missing_tables": sorted(expected - present),
        "valid": present == expected and column_total == sum(int(table["column_count"]) for table in contract["tables"]),
    }


def write_ddl() -> tuple[dict[str, Any], str]:
    contract = _contract()
    ddl = render_ddl(contract)
    DDL_PATH.parent.mkdir(parents=True, exist_ok=True)
    DDL_PATH.write_text(ddl, encoding="utf-8")
    validation = validate_ddl(contract, ddl)
    if not validation["valid"]:
        raise RuntimeError(validation)
    return contract, ddl


def load(client: ClickHouseHttpClient, contract: dict[str, Any], ddl: str, profile: str) -> dict[str, Any]:
    client.wait_until_ready()
    for statement in split_sql_statements(ddl):
        client.execute(statement)
    grant_reader_access(client)
    scale = PROFILE_SCALE[profile]
    expected_counts = {}
    for table in contract["tables"]:
        qualified = f"{DATABASE}.`{table['name']}`"
        rows = _row_count(table, scale)
        client.execute(f"TRUNCATE TABLE {qualified}")
        client.execute(insert_sql(table, rows))
        expected_counts[table["name"]] = rows
    observed_counts = {
        table["name"]: int(client.execute(f"SELECT count() FROM {DATABASE}.`{table['name']}`").strip())
        for table in contract["tables"]
    }
    if observed_counts != expected_counts:
        raise RuntimeError("loaded row counts do not match deterministic plan")
    orphan_counts = {
        name: int(client.execute(relation_integrity_sql(*relation)).strip())
        for name, relation in RELATION_INTEGRITY_CHECKS.items()
    }
    if any(orphan_counts.values()):
        raise RuntimeError(f"referential integrity checks failed: {orphan_counts}")
    snapshot = {
        "snapshot_id": f"production-like-{profile}-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "database": DATABASE,
        "profile": profile,
        "schema_contract": str(CONTRACT.relative_to(ROOT)),
        "ddl_sha256": hashlib.sha256(ddl.encode()).hexdigest(),
        "table_row_counts": observed_counts,
        "total_rows": sum(observed_counts.values()),
        "target_minimum_rows_met": sum(observed_counts.values()) >= 5_000_000,
        "referential_integrity_orphan_rows": orphan_counts,
        "referential_integrity_valid": True,
    }
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILE_SCALE), default="smoke")
    parser.add_argument("--ddl-only", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--user", default="data_agent")
    parser.add_argument("--password", default="data_agent_dev")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract, ddl = write_ddl()
    print(json.dumps(validate_ddl(contract, ddl), ensure_ascii=False, indent=2))
    if args.ddl_only:
        print(DDL_PATH)
        return 0
    client = ClickHouseHttpClient(args.host, args.port, args.user, args.password, timeout=600)
    print(json.dumps(load(client, contract, ddl, args.profile), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
