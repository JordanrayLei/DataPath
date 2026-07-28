from __future__ import annotations

import pytest

from app.warehouse.clickhouse import ClickHouseClient


class RecordingClient(ClickHouseClient):
    def __init__(self) -> None:
        super().__init__("127.0.0.1", 8123, "user", "password")
        self.params = None

    def execute(self, sql: str, params: dict | None = None) -> str:
        self.params = params
        return "123\n"


@pytest.mark.parametrize(
    ("table", "database"),
    [("production_benchmark.fct_orders", "production_benchmark")],
)
def test_estimate_rows_allows_only_explicit_warehouse_databases(
    table: str, database: str
) -> None:
    client = RecordingClient()
    assert client.estimate_table_rows(table) == 123
    assert client.params == {"database": database, "table": table.split(".", 1)[1]}


@pytest.mark.parametrize(
    "table",
    [
        "system.parts",
        "data_warehouse.orders",
        "other.orders",
        "production_benchmark.orders.extra",
        "production_benchmark.orders;drop_table",
        "production_benchmark.Orders",
    ],
)
def test_estimate_rows_rejects_other_databases_and_invalid_identifiers(table: str) -> None:
    with pytest.raises(ValueError, match="outside the allowed warehouse database"):
        RecordingClient().estimate_table_rows(table)
