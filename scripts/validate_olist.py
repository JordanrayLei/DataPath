"""Validate Olist row counts, primary keys, and future join paths in ClickHouse."""

from __future__ import annotations

import argparse

from scripts.clickhouse_http import ClickHouseHttpClient


EXPECTED_MINIMUM_ROWS = {
    "olist_customers": 90_000,
    "olist_orders": 90_000,
    "olist_order_items": 100_000,
    "olist_order_payments": 90_000,
    "olist_order_reviews": 90_000,
    "olist_products": 30_000,
    "olist_sellers": 3_000,
    "olist_geolocation": 900_000,
    "olist_product_category_translation": 70,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--user", default="data_agent")
    parser.add_argument("--password", default="data_agent_dev")
    return parser.parse_args()


def scalar(client: ClickHouseHttpClient, sql: str) -> int:
    return int(client.execute(sql).strip() or 0)


def main() -> None:
    args = parse_args()
    client = ClickHouseHttpClient(args.host, args.port, args.user, args.password)
    client.wait_until_ready()
    for table, minimum in EXPECTED_MINIMUM_ROWS.items():
        count = scalar(client, f"SELECT count() FROM data_warehouse.{table}")
        if count < minimum:
            raise AssertionError(f"{table} has {count:,} rows; expected at least {minimum:,}")
        print(f"PASS rows: {table}={count:,}")

    checks = {
        "customer primary key": """
            SELECT count() FROM
            (SELECT customer_id FROM data_warehouse.olist_customers GROUP BY customer_id HAVING count() > 1)
        """,
        "order primary key": """
            SELECT count() FROM
            (SELECT order_id FROM data_warehouse.olist_orders GROUP BY order_id HAVING count() > 1)
        """,
        "product primary key": """
            SELECT count() FROM
            (SELECT product_id FROM data_warehouse.olist_products GROUP BY product_id HAVING count() > 1)
        """,
        "seller primary key": """
            SELECT count() FROM
            (SELECT seller_id FROM data_warehouse.olist_sellers GROUP BY seller_id HAVING count() > 1)
        """,
        "orders to customers": """
            SELECT count() FROM data_warehouse.olist_orders o
            LEFT JOIN data_warehouse.olist_customers c ON o.customer_id = c.customer_id
            WHERE c.customer_id = ''
        """,
        "items to orders": """
            SELECT count() FROM data_warehouse.olist_order_items i
            LEFT JOIN data_warehouse.olist_orders o ON i.order_id = o.order_id
            WHERE o.order_id = ''
        """,
        "items to products": """
            SELECT count() FROM data_warehouse.olist_order_items i
            LEFT JOIN data_warehouse.olist_products p ON i.product_id = p.product_id
            WHERE p.product_id = ''
        """,
        "items to sellers": """
            SELECT count() FROM data_warehouse.olist_order_items i
            LEFT JOIN data_warehouse.olist_sellers s ON i.seller_id = s.seller_id
            WHERE s.seller_id = ''
        """,
        "payments to orders": """
            SELECT count() FROM data_warehouse.olist_order_payments p
            LEFT JOIN data_warehouse.olist_orders o ON p.order_id = o.order_id
            WHERE o.order_id = ''
        """,
        "reviews to orders": """
            SELECT count() FROM data_warehouse.olist_order_reviews r
            LEFT JOIN data_warehouse.olist_orders o ON r.order_id = o.order_id
            WHERE o.order_id = ''
        """,
    }
    for name, sql in checks.items():
        failures = scalar(client, sql)
        if failures:
            raise AssertionError(f"{name} has {failures:,} invalid rows")
        print(f"PASS relation: {name}")


if __name__ == "__main__":
    main()
