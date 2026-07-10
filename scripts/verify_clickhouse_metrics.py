"""Compare six ClickHouse metric baselines with the deterministic data manifest."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from clickhouse_http import ClickHouseHttpClient


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "generated"
BASELINE_SQL_PATH = ROOT / "sql" / "baseline_metrics.sql"
TOLERANCE = Decimal("0.01")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--user", default="chatbi_reader")
    parser.add_argument("--password", default="chatbi_reader_dev")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    expected = {
        **manifest["sales"]["metrics"],
        "M_AD_ROAS": manifest["advertising"]["metrics"]["M_AD_ROAS"],
    }

    client = ClickHouseHttpClient(args.host, args.port, args.user, args.password)
    client.wait_until_ready()
    output = client.execute(BASELINE_SQL_PATH.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in output.splitlines() if line.strip()]
    actual = {row["metric_id"]: row["value"] for row in rows}

    if set(actual) != set(expected):
        raise AssertionError(
            f"Metric ID mismatch: actual={sorted(actual)}, expected={sorted(expected)}"
        )

    for metric_id, expected_value in expected.items():
        actual_value = Decimal(actual[metric_id])
        if abs(actual_value - Decimal(str(expected_value))) > TOLERANCE:
            raise AssertionError(
                f"{metric_id} mismatch: ClickHouse={actual_value}, manifest={expected_value}"
            )
        print(f"PASS: {metric_id} = {actual_value}")


if __name__ == "__main__":
    main()
