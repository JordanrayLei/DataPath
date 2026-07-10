"""Create ClickHouse tables, load generated CSV files, and rebuild DWD/DWS models."""

from __future__ import annotations

import argparse
from pathlib import Path

from clickhouse_http import ClickHouseHttpClient, split_sql_statements


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "generated"
SCHEMA_PATH = ROOT / "infra" / "clickhouse" / "init" / "01-schema.sql"
REBUILD_PATH = ROOT / "infra" / "clickhouse" / "sql" / "10-rebuild-models.sql"


def run_sql_file(client: ClickHouseHttpClient, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    statements = split_sql_statements(text)
    for index, statement in enumerate(statements, start=1):
        client.execute(statement)
        print(f"Applied {path.name} statement {index}/{len(statements)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--user", default="data_agent")
    parser.add_argument("--password", default="data_agent_dev")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = ClickHouseHttpClient(args.host, args.port, args.user, args.password)
    client.wait_until_ready()
    run_sql_file(client, SCHEMA_PATH)

    client.execute("TRUNCATE TABLE data_warehouse.ods_sales_order_item")
    client.execute("TRUNCATE TABLE data_warehouse.ods_ad_delivery_day")

    data_dir = args.data_dir.resolve()
    client.insert_csv_with_names(
        "data_warehouse.ods_sales_order_item",
        data_dir / "sales_order_items.csv",
    )
    print("Loaded sales_order_items.csv")
    client.insert_csv_with_names(
        "data_warehouse.ods_ad_delivery_day",
        data_dir / "ad_delivery_daily.csv",
    )
    print("Loaded ad_delivery_daily.csv")

    run_sql_file(client, REBUILD_PATH)
    print("ClickHouse ODS, DWD, and DWS models are ready")


if __name__ == "__main__":
    main()

