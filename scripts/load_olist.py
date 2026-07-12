"""Load the nine-table Olist Brazilian E-Commerce dataset into ClickHouse."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.clickhouse_http import ClickHouseHttpClient, split_sql_statements
from scripts.download_olist import EXPECTED_FILES
from scripts.seed_olist_staging import seed as seed_staging_models


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "external" / "olist"
SCHEMA = ROOT / "infra" / "clickhouse" / "sql" / "30-olist-brazilian-ecommerce.sql"
FILE_TABLES = {
    "olist_customers_dataset.csv": "olist_customers",
    "olist_orders_dataset.csv": "olist_orders",
    "olist_order_items_dataset.csv": "olist_order_items",
    "olist_order_payments_dataset.csv": "olist_order_payments",
    "olist_order_reviews_dataset.csv": "olist_order_reviews",
    "olist_products_dataset.csv": "olist_products",
    "olist_sellers_dataset.csv": "olist_sellers",
    "olist_geolocation_dataset.csv": "olist_geolocation",
    "product_category_name_translation.csv": "olist_product_category_translation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--user", default="data_agent")
    parser.add_argument("--password", default="data_agent_dev")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    missing = EXPECTED_FILES - {path.name for path in args.data_dir.glob("*.csv")}
    if missing:
        raise FileNotFoundError(f"Olist CSV files are missing: {sorted(missing)}")

    client = ClickHouseHttpClient(args.host, args.port, args.user, args.password)
    client.wait_until_ready()
    for statement in split_sql_statements(SCHEMA.read_text(encoding="utf-8")):
        client.execute(statement)
    for filename, table in FILE_TABLES.items():
        qualified_table = f"data_warehouse.{table}"
        client.execute(f"TRUNCATE TABLE {qualified_table}")
        client.insert_csv_with_names(qualified_table, args.data_dir / filename)
        count = int(client.execute(f"SELECT count() FROM {qualified_table}").strip())
        print(f"Loaded {count:,} rows into {qualified_table}")
    seed_staging_models()


if __name__ == "__main__":
    main()
