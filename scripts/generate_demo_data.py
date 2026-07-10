"""Generate deterministic sales and advertising demo data for ClickHouse."""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "generated"
SEED = 20260707
START_DATE = date(2025, 7, 1)
END_DATE = date(2026, 6, 30)
MONEY = Decimal("0.01")

PROFILE_ORDERS = {
    "smoke": 5_000,
    "demo": 100_000,
    "portfolio": 600_000,
}


@dataclass(frozen=True)
class Product:
    product_id: str
    product_name: str
    category_id: str
    category_name: str
    base_price: Decimal
    cost_rate: Decimal


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    campaign_name: str
    platform: str
    account: str
    base_impressions: int
    base_ctr: float
    base_cvr: float
    base_cpc: float
    average_order_value: float


PRODUCTS = [
    Product("P001", "无线耳机", "C_ELECTRONICS", "数码", Decimal("399"), Decimal("0.58")),
    Product("P002", "智能手表", "C_ELECTRONICS", "数码", Decimal("899"), Decimal("0.62")),
    Product("P003", "机械键盘", "C_ELECTRONICS", "数码", Decimal("529"), Decimal("0.55")),
    Product("P004", "便携充电器", "C_ELECTRONICS", "数码", Decimal("169"), Decimal("0.48")),
    Product("P005", "保湿面霜", "C_BEAUTY", "美妆", Decimal("239"), Decimal("0.32")),
    Product("P006", "防晒乳", "C_BEAUTY", "美妆", Decimal("159"), Decimal("0.28")),
    Product("P007", "精华液", "C_BEAUTY", "美妆", Decimal("329"), Decimal("0.35")),
    Product("P008", "坚果礼盒", "C_FOOD", "食品", Decimal("129"), Decimal("0.61")),
    Product("P009", "精品咖啡", "C_FOOD", "食品", Decimal("99"), Decimal("0.52")),
    Product("P010", "低糖麦片", "C_FOOD", "食品", Decimal("69"), Decimal("0.49")),
    Product("P011", "护颈枕", "C_HOME", "家居", Decimal("189"), Decimal("0.43")),
    Product("P012", "香薰机", "C_HOME", "家居", Decimal("219"), Decimal("0.46")),
    Product("P013", "收纳套装", "C_HOME", "家居", Decimal("119"), Decimal("0.39")),
    Product("P014", "瑜伽垫", "C_SPORTS", "运动", Decimal("179"), Decimal("0.41")),
    Product("P015", "运动水杯", "C_SPORTS", "运动", Decimal("89"), Decimal("0.37")),
    Product("P016", "跑步腰包", "C_SPORTS", "运动", Decimal("109"), Decimal("0.40")),
    Product("P017", "轻量羽绒服", "C_APPAREL", "服饰", Decimal("599"), Decimal("0.45")),
    Product("P018", "基础卫衣", "C_APPAREL", "服饰", Decimal("229"), Decimal("0.42")),
]

REGIONS = {
    "华东": ["上海", "浙江", "江苏", "山东"],
    "华南": ["广东", "福建", "广西"],
    "华北": ["北京", "天津", "河北"],
    "西南": ["四川", "重庆", "云南"],
}

CAMPAIGNS = [
    Campaign("CMP_EAST_GROWTH", "华东新客增长", "ocean", "ACC_OCEAN_01", 38_000, 0.040, 0.060, 2.4, 340),
    Campaign("CMP_BRAND_SEARCH", "品牌搜索承接", "search", "ACC_SEARCH_01", 21_000, 0.065, 0.085, 3.2, 410),
    Campaign("CMP_WECHAT_REMARKET", "微信老客召回", "wechat", "ACC_WECHAT_01", 18_000, 0.032, 0.095, 2.8, 370),
    Campaign("CMP_PRODUCT_LAUNCH", "新品上市", "ocean", "ACC_OCEAN_01", 31_000, 0.035, 0.052, 2.6, 390),
    Campaign("CMP_SOUTH_PROMO", "华南促销", "wechat", "ACC_WECHAT_02", 26_000, 0.030, 0.070, 2.1, 280),
    Campaign("CMP_ALWAYS_ON", "常青商品推广", "search", "ACC_SEARCH_02", 16_000, 0.072, 0.078, 3.0, 320),
]


def quantize(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def decimal_text(value: Decimal) -> str:
    return format(value.quantize(MONEY), "f")


def date_sequence(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def build_weighted_dates() -> tuple[list[date], list[float]]:
    dates = date_sequence(START_DATE, END_DATE)
    cumulative: list[float] = []
    total = 0.0
    for current in dates:
        weight = 0.86 if current.weekday() >= 5 else 1.0
        if current.month == 11 and 1 <= current.day <= 12:
            weight *= 2.8
        if current.month == 6 and 1 <= current.day <= 18:
            weight *= 2.1
        if current.month in {1, 2}:
            weight *= 0.82
        total += weight
        cumulative.append(total)
    return dates, cumulative


def choose_weighted_date(rng: random.Random, dates: list[date], cumulative: list[float]) -> date:
    target = rng.random() * cumulative[-1]
    return dates[bisect.bisect_left(cumulative, target)]


def write_sales_data(output: Path, orders: int, rng: random.Random) -> dict[str, object]:
    path = output / "sales_order_items.csv"
    headers = [
        "order_id",
        "order_item_id",
        "user_id",
        "product_id",
        "product_name",
        "category_id",
        "category_name",
        "region",
        "province",
        "sales_channel",
        "created_at",
        "paid_at",
        "order_status",
        "quantity",
        "unit_price",
        "gross_amount",
        "paid_amount",
        "refund_amount",
        "item_cost",
        "is_test",
    ]

    dates, cumulative = build_weighted_dates()
    user_pool = max(2_000, orders // 4)
    item_rows = 0
    valid_orders: set[str] = set()
    gmv = Decimal("0")
    paid_revenue = Decimal("0")
    refund_amount = Decimal("0")
    gross_profit = Decimal("0")
    anomaly_paid = Decimal("0")
    anomaly_refund = Decimal("0")
    baseline_paid = Decimal("0")
    baseline_refund = Decimal("0")

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()

        for order_index in range(1, orders + 1):
            order_id = f"O{order_index:09d}"
            user_id = f"U{rng.randint(1, user_pool):08d}"
            order_date = choose_weighted_date(rng, dates, cumulative)
            created_at = datetime.combine(
                order_date,
                time(rng.randint(7, 23), rng.randint(0, 59), rng.randint(0, 59)),
            )
            is_test = 1 if rng.random() < 0.002 else 0
            is_cancelled = rng.random() < 0.03
            paid_at = None if is_cancelled else created_at + timedelta(minutes=rng.randint(1, 180))
            region = rng.choices(list(REGIONS), weights=[0.34, 0.27, 0.22, 0.17], k=1)[0]
            province = rng.choice(REGIONS[region])
            channel = rng.choices(["app", "web", "offline"], weights=[0.52, 0.30, 0.18], k=1)[0]
            item_count = rng.choices([1, 2, 3], weights=[0.64, 0.29, 0.07], k=1)[0]
            products = rng.sample(PRODUCTS, k=item_count)

            for item_index, product in enumerate(products, start=1):
                quantity = rng.choices([1, 2, 3], weights=[0.79, 0.17, 0.04], k=1)[0]
                price_factor = Decimal(str(rng.uniform(0.93, 1.08)))
                unit_price = quantize(product.base_price * price_factor)
                gross = quantize(unit_price * quantity)
                discount = Decimal(str(rng.uniform(0.86, 0.99)))
                paid = Decimal("0") if is_cancelled else quantize(gross * discount)

                refund_probability = 0.055
                is_refund_anomaly = (
                    order_date.year == 2026
                    and order_date.month == 3
                    and region == "华东"
                    and product.category_id == "C_ELECTRONICS"
                )
                if is_refund_anomaly:
                    refund_probability = 0.40

                refund_ratio = Decimal("0")
                if not is_cancelled and rng.random() < refund_probability:
                    refund_ratio = rng.choice([Decimal("0.30"), Decimal("0.50"), Decimal("1.00")])
                refunded = quantize(paid * refund_ratio)
                recognized_cost = (
                    Decimal("0")
                    if is_cancelled
                    else quantize(unit_price * quantity * product.cost_rate * (Decimal("1") - refund_ratio))
                )

                if is_cancelled:
                    status = "cancelled"
                elif refund_ratio == Decimal("1"):
                    status = "refunded"
                elif refund_ratio > 0:
                    status = "partially_refunded"
                else:
                    status = "paid"

                writer.writerow(
                    {
                        "order_id": order_id,
                        "order_item_id": f"{order_id}-I{item_index}",
                        "user_id": user_id,
                        "product_id": product.product_id,
                        "product_name": product.product_name,
                        "category_id": product.category_id,
                        "category_name": product.category_name,
                        "region": region,
                        "province": province,
                        "sales_channel": channel,
                        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "paid_at": "" if paid_at is None else paid_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "order_status": status,
                        "quantity": quantity,
                        "unit_price": decimal_text(unit_price),
                        "gross_amount": decimal_text(gross),
                        "paid_amount": decimal_text(paid),
                        "refund_amount": decimal_text(refunded),
                        "item_cost": decimal_text(recognized_cost),
                        "is_test": is_test,
                    }
                )
                item_rows += 1

                if not is_cancelled and not is_test:
                    valid_orders.add(order_id)
                    gmv += gross
                    paid_revenue += paid
                    refund_amount += refunded
                    gross_profit += paid - refunded - recognized_cost
                    if is_refund_anomaly:
                        anomaly_paid += paid
                        anomaly_refund += refunded
                    elif product.category_id == "C_ELECTRONICS":
                        baseline_paid += paid
                        baseline_refund += refunded

    net_revenue = paid_revenue - refund_amount
    gross_margin_rate = Decimal("0") if net_revenue == 0 else gross_profit / net_revenue
    anomaly_refund_rate = Decimal("0") if anomaly_paid == 0 else anomaly_refund / anomaly_paid
    baseline_refund_rate = Decimal("0") if baseline_paid == 0 else baseline_refund / baseline_paid

    return {
        "file": path.name,
        "rows": item_rows,
        "orders_requested": orders,
        "valid_paid_orders": len(valid_orders),
        "metrics": {
            "M_SALES_GMV": decimal_text(gmv),
            "M_SALES_PAID_REVENUE": decimal_text(paid_revenue),
            "M_SALES_ORDER_COUNT": len(valid_orders),
            "M_SALES_GROSS_PROFIT": decimal_text(gross_profit),
            "M_SALES_GROSS_MARGIN_RATE": decimal_text(gross_margin_rate * 100),
        },
        "anomaly": {
            "name": "east_electronics_march_refund_spike",
            "refund_rate_percent": decimal_text(anomaly_refund_rate * 100),
            "baseline_refund_rate_percent": decimal_text(baseline_refund_rate * 100),
        },
    }


def write_ad_data(output: Path, rng: random.Random) -> dict[str, object]:
    path = output / "ad_delivery_daily.csv"
    headers = [
        "biz_date",
        "ad_platform",
        "ad_account",
        "campaign_id",
        "campaign_name",
        "creative_id",
        "device_type",
        "attribution_window",
        "impressions",
        "clicks",
        "spend",
        "conversions",
        "attributed_revenue",
    ]

    row_count = 0
    total_spend = Decimal("0")
    total_revenue = Decimal("0")
    anomaly_spend = Decimal("0")
    anomaly_revenue = Decimal("0")
    baseline_spend = Decimal("0")
    baseline_revenue = Decimal("0")

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()

        for biz_date in date_sequence(START_DATE, END_DATE):
            seasonal = 1.0
            if biz_date.month == 11 and biz_date.day <= 12:
                seasonal = 1.7
            elif biz_date.month == 6 and biz_date.day <= 18:
                seasonal = 1.45
            elif biz_date.weekday() >= 5:
                seasonal = 0.9

            for campaign in CAMPAIGNS:
                for creative_number in (1, 2):
                    for device in ("ios", "android"):
                        jitter = rng.uniform(0.82, 1.18)
                        impressions = max(
                            100,
                            int(campaign.base_impressions * seasonal * jitter / 4),
                        )
                        ctr = campaign.base_ctr * rng.uniform(0.88, 1.12)
                        cvr = campaign.base_cvr * rng.uniform(0.85, 1.15)
                        cpc = campaign.base_cpc * rng.uniform(0.90, 1.10)

                        is_efficiency_anomaly = (
                            campaign.campaign_id == "CMP_EAST_GROWTH"
                            and biz_date.year == 2026
                            and biz_date.month == 4
                        )
                        if is_efficiency_anomaly:
                            cpc *= 1.80
                            cvr *= 0.40

                        clicks = min(impressions, max(0, int(impressions * ctr)))
                        conversions = min(clicks, max(0, int(clicks * cvr)))
                        spend = quantize(clicks * cpc)
                        revenue_per_conversion = campaign.average_order_value * rng.uniform(0.88, 1.12)
                        attributed_revenue = quantize(conversions * revenue_per_conversion)

                        writer.writerow(
                            {
                                "biz_date": biz_date.isoformat(),
                                "ad_platform": campaign.platform,
                                "ad_account": campaign.account,
                                "campaign_id": campaign.campaign_id,
                                "campaign_name": campaign.campaign_name,
                                "creative_id": f"{campaign.campaign_id}-CR{creative_number}",
                                "device_type": device,
                                "attribution_window": "7d",
                                "impressions": impressions,
                                "clicks": clicks,
                                "spend": decimal_text(spend),
                                "conversions": conversions,
                                "attributed_revenue": decimal_text(attributed_revenue),
                            }
                        )
                        row_count += 1
                        total_spend += spend
                        total_revenue += attributed_revenue

                        if is_efficiency_anomaly:
                            anomaly_spend += spend
                            anomaly_revenue += attributed_revenue
                        elif campaign.campaign_id == "CMP_EAST_GROWTH" and biz_date.month == 3 and biz_date.year == 2026:
                            baseline_spend += spend
                            baseline_revenue += attributed_revenue

    roas = Decimal("0") if total_spend == 0 else total_revenue / total_spend
    anomaly_roas = Decimal("0") if anomaly_spend == 0 else anomaly_revenue / anomaly_spend
    baseline_roas = Decimal("0") if baseline_spend == 0 else baseline_revenue / baseline_spend

    return {
        "file": path.name,
        "rows": row_count,
        "metrics": {
            "M_AD_SPEND": decimal_text(total_spend),
            "M_AD_ATTRIBUTED_REVENUE": decimal_text(total_revenue),
            "M_AD_ROAS": decimal_text(roas),
        },
        "anomaly": {
            "name": "east_growth_april_efficiency_drop",
            "april_roas": decimal_text(anomaly_roas),
            "march_roas": decimal_text(baseline_roas),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILE_ORDERS), default="demo")
    parser.add_argument("--orders", type=int, help="Override order count for the selected profile")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    orders = args.orders if args.orders is not None else PROFILE_ORDERS[args.profile]
    if orders < 100:
        raise SystemExit("--orders must be at least 100")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    sales = write_sales_data(output, orders, rng)
    advertising = write_ad_data(output, rng)
    manifest = {
        "schema_version": "1.0",
        "profile": args.profile,
        "seed": args.seed,
        "date_range": {"start": START_DATE.isoformat(), "end": END_DATE.isoformat()},
        "sales": sales,
        "advertising": advertising,
    }

    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {sales['rows']:,} sales rows and {advertising['rows']:,} ad rows")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
