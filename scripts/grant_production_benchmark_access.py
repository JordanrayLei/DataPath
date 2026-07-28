"""Grant and verify read-only access to the production benchmark warehouse."""

from __future__ import annotations

import argparse

from scripts.build_production_like_warehouse import (
    DATABASE,
    READER_USER,
    grant_reader_access,
)
from scripts.clickhouse_http import ClickHouseHttpClient


def grant_and_verify(
    admin: ClickHouseHttpClient,
    reader: ClickHouseHttpClient,
) -> int:
    admin.wait_until_ready()
    grant_reader_access(admin)
    return int(reader.execute(f"SELECT count() FROM {DATABASE}.fct_orders").strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--admin-user", default="data_agent")
    parser.add_argument("--admin-password", default="data_agent_dev")
    parser.add_argument("--reader-user", default=READER_USER)
    parser.add_argument("--reader-password", default="chatbi_reader_dev")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.reader_user != READER_USER:
        raise ValueError(f"reader user must be {READER_USER!r}")
    admin = ClickHouseHttpClient(
        args.host, args.port, args.admin_user, args.admin_password
    )
    reader = ClickHouseHttpClient(
        args.host, args.port, args.reader_user, args.reader_password
    )
    row_count = grant_and_verify(admin, reader)
    print(
        f"Granted SELECT ON {DATABASE}.* TO {READER_USER}; "
        f"verified fct_orders rows={row_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
