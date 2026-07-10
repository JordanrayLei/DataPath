"""Validate generated demo CSV invariants and metric baselines."""

from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "generated"
TOLERANCE = Decimal("0.01")


def close_enough(actual: Decimal, expected: Decimal) -> bool:
    return abs(actual - expected) <= TOLERANCE


def validate_sales(data_dir: Path, manifest: dict) -> None:
    path = data_dir / manifest["file"]
    rows = 0
    valid_orders: set[str] = set()
    gmv = Decimal("0")
    paid_revenue = Decimal("0")
    refunds = Decimal("0")
    gross_profit = Decimal("0")
    anomaly_paid = Decimal("0")
    anomaly_refund = Decimal("0")
    baseline_paid = Decimal("0")
    baseline_refund = Decimal("0")

    with path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            rows += 1
            gross = Decimal(row["gross_amount"])
            paid = Decimal(row["paid_amount"])
            refund = Decimal(row["refund_amount"])
            item_cost = Decimal(row["item_cost"])
            if min(gross, paid, refund, item_cost) < 0:
                raise AssertionError(f"Negative sales amount at row {rows}")
            if refund > paid:
                raise AssertionError(f"Refund exceeds paid amount at row {rows}")

            cancelled = row["order_status"] == "cancelled"
            is_test = row["is_test"] == "1"
            if cancelled and (row["paid_at"] or paid != 0):
                raise AssertionError(f"Cancelled order has payment at row {rows}")
            if cancelled or is_test:
                continue

            valid_orders.add(row["order_id"])
            gmv += gross
            paid_revenue += paid
            refunds += refund
            gross_profit += paid - refund - item_cost

            paid_date = row["paid_at"][:10]
            is_anomaly = (
                paid_date.startswith("2026-03")
                and row["region"] == "华东"
                and row["category_id"] == "C_ELECTRONICS"
            )
            if is_anomaly:
                anomaly_paid += paid
                anomaly_refund += refund
            elif row["category_id"] == "C_ELECTRONICS":
                baseline_paid += paid
                baseline_refund += refund

    if rows != manifest["rows"]:
        raise AssertionError(f"Sales row count mismatch: {rows} != {manifest['rows']}")

    net_revenue = paid_revenue - refunds
    margin_rate = Decimal("0") if net_revenue == 0 else gross_profit / net_revenue * 100
    expected = manifest["metrics"]
    actual_metrics = {
        "M_SALES_GMV": gmv,
        "M_SALES_PAID_REVENUE": paid_revenue,
        "M_SALES_ORDER_COUNT": Decimal(len(valid_orders)),
        "M_SALES_GROSS_PROFIT": gross_profit,
        "M_SALES_GROSS_MARGIN_RATE": margin_rate,
    }
    for metric_id, actual in actual_metrics.items():
        if not close_enough(actual, Decimal(str(expected[metric_id]))):
            raise AssertionError(f"{metric_id} mismatch: {actual} != {expected[metric_id]}")

    anomaly_rate = anomaly_refund / anomaly_paid if anomaly_paid else Decimal("0")
    baseline_rate = baseline_refund / baseline_paid if baseline_paid else Decimal("0")
    if anomaly_rate <= baseline_rate * Decimal("2"):
        raise AssertionError(
            f"Refund anomaly is not strong enough: anomaly={anomaly_rate}, baseline={baseline_rate}"
        )


def validate_advertising(data_dir: Path, manifest: dict) -> None:
    path = data_dir / manifest["file"]
    rows = 0
    spend = Decimal("0")
    revenue = Decimal("0")
    anomaly_spend = Decimal("0")
    anomaly_revenue = Decimal("0")
    baseline_spend = Decimal("0")
    baseline_revenue = Decimal("0")

    with path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            rows += 1
            impressions = int(row["impressions"])
            clicks = int(row["clicks"])
            conversions = int(row["conversions"])
            row_spend = Decimal(row["spend"])
            row_revenue = Decimal(row["attributed_revenue"])
            if not (0 <= conversions <= clicks <= impressions):
                raise AssertionError(f"Invalid advertising funnel at row {rows}")
            if row_spend < 0 or row_revenue < 0:
                raise AssertionError(f"Negative advertising amount at row {rows}")

            spend += row_spend
            revenue += row_revenue
            if row["campaign_id"] == "CMP_EAST_GROWTH":
                if row["biz_date"].startswith("2026-04"):
                    anomaly_spend += row_spend
                    anomaly_revenue += row_revenue
                elif row["biz_date"].startswith("2026-03"):
                    baseline_spend += row_spend
                    baseline_revenue += row_revenue

    if rows != manifest["rows"]:
        raise AssertionError(f"Advertising row count mismatch: {rows} != {manifest['rows']}")

    roas = Decimal("0") if spend == 0 else revenue / spend
    expected = manifest["metrics"]
    actual_metrics = {
        "M_AD_SPEND": spend,
        "M_AD_ATTRIBUTED_REVENUE": revenue,
        "M_AD_ROAS": roas,
    }
    for metric_id, actual in actual_metrics.items():
        if not close_enough(actual, Decimal(str(expected[metric_id]))):
            raise AssertionError(f"{metric_id} mismatch: {actual} != {expected[metric_id]}")

    anomaly_roas = anomaly_revenue / anomaly_spend if anomaly_spend else Decimal("0")
    baseline_roas = baseline_revenue / baseline_spend if baseline_spend else Decimal("0")
    if anomaly_roas >= baseline_roas * Decimal("0.60"):
        raise AssertionError(
            f"ROAS anomaly is not strong enough: anomaly={anomaly_roas}, baseline={baseline_roas}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    validate_sales(data_dir, manifest["sales"])
    print("PASS: sales rows, invariants, five metric baselines, and refund anomaly")
    validate_advertising(data_dir, manifest["advertising"])
    print("PASS: ad rows, funnel invariants, ROAS baseline, and efficiency anomaly")


if __name__ == "__main__":
    main()
