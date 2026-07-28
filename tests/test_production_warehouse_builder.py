from __future__ import annotations

from scripts.build_production_like_warehouse import (
    FACT_WEIGHTS,
    PROFILE_SCALE,
    RELATION_INTEGRITY_CHECKS,
    _contract,
    _expression,
    _row_count,
    grant_reader_access,
    relation_integrity_sql,
    render_ddl,
    table_columns,
    validate_ddl,
)


def test_generated_ddl_matches_all_contract_tables_and_columns() -> None:
    contract = _contract()
    ddl = render_ddl(contract)
    validation = validate_ddl(contract, ddl)
    assert validation["valid"] is True
    assert validation["table_count"] == 42
    assert validation["column_count"] == 442
    assert "production_benchmark.`fct_order_items`" in ddl
    assert "production_benchmark.`dim_customer_scd2`" in ddl


def test_reader_access_is_limited_to_production_benchmark() -> None:
    class RecordingClient:
        sql = ""

        def execute(self, sql: str) -> str:
            self.sql = sql
            return ""

    client = RecordingClient()
    grant_reader_access(client)  # type: ignore[arg-type]
    assert client.sql == "GRANT SELECT ON production_benchmark.* TO chatbi_reader"


def test_relation_keys_are_present_in_core_fact_tables() -> None:
    tables = {table["name"]: table for table in _contract()["tables"]}
    order_columns = {name for name, _ in table_columns(tables["fct_orders"])}
    item_columns = {name for name, _ in table_columns(tables["fct_order_items"])}
    assert {"order_id", "customer_sk", "tenant_id"} <= order_columns
    assert {"order_item_id", "order_id", "product_sk", "seller_sk"} <= item_columns


def test_production_profile_plans_more_than_five_million_rows() -> None:
    contract = _contract()
    scale = PROFILE_SCALE["production"]
    total = sum(_row_count(table, scale) for table in contract["tables"])
    assert total >= 5_000_000
    assert set(FACT_WEIGHTS) == {table["name"] for table in contract["tables"] if table["kind"] == "fact"}


def test_generated_dates_span_snapshot_and_dimensions_have_realistic_cardinality() -> None:
    assert "2654435761" in _expression("business_date", "Date")
    assert "number % 5" in _expression("currency_code", "LowCardinality(String)")
    assert "number % 7" in _expression("status_code", "LowCardinality(String)")
    assert "number % 7" in _expression("region_code", "LowCardinality(String)")


def test_fact_foreign_keys_fit_their_dimension_and_parent_key_domains() -> None:
    assert "% 500000" in _expression("order_id", "UInt64")
    assert "% 600000" in _expression("payment_id", "UInt64")
    assert "% 50000" in _expression("warehouse_sk", "UInt64")
    assert "% 50000" in _expression("customer_sk", "UInt64")
    assert len(RELATION_INTEGRITY_CHECKS) == 9
    sql = relation_integrity_sql("fct_shipments", "dim_warehouse", "warehouse_sk")
    assert "LEFT ANTI JOIN production_benchmark.`dim_warehouse`" in sql
    assert "child.`warehouse_sk` = parent.`warehouse_sk`" in sql
