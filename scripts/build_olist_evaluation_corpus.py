"""Build the deterministic Olist V1 product evaluation corpus."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "evaluation" / "olist_business_cases.json"


def success(name: str, query: str, metric: str, **expected: object) -> dict[str, object]:
    return {
        "name": name, "category": "olist_success", "query": query, "domain": "auto",
        "expected_status": "SUCCESS", "expected_metric": metric, **expected,
    }


def build() -> list[dict[str, object]]:
    cases = [
        success("revenue_total_2017", "2017年Olist销售额", "M_OLIST_ITEM_REVENUE", expected_intent="aggregate_query"),
        success("revenue_month_2017", "2017年每月Olist销售额趋势", "M_OLIST_ITEM_REVENUE", expected_intent="trend_query", expected_dimension="D_MONTH", expected_chart="line"),
        success("revenue_category", "2017年各商品品类Olist销售额排名", "M_OLIST_ITEM_REVENUE", expected_intent="ranking_query", expected_dimension="D_OLIST_CATEGORY"),
        success("revenue_customer_state", "2017年各客户州Olist销售额", "M_OLIST_ITEM_REVENUE", expected_dimension="D_OLIST_CUSTOMER_STATE"),
        success("revenue_seller_state", "2017年各卖家州Olist销售额", "M_OLIST_ITEM_REVENUE", expected_dimension="D_OLIST_SELLER_STATE"),
        success("revenue_status", "2017年各订单状态Olist销售额", "M_OLIST_ITEM_REVENUE", expected_dimension="D_OLIST_ORDER_STATUS"),
        success("freight_total_2017", "2017年Olist运费", "M_OLIST_FREIGHT_VALUE"),
        success("freight_month_2017", "2017年每月Olist物流费趋势", "M_OLIST_FREIGHT_VALUE", expected_dimension="D_MONTH", expected_chart="line"),
        success("freight_category", "2017年各品类Olist配送费", "M_OLIST_FREIGHT_VALUE", expected_dimension="D_OLIST_CATEGORY"),
        success("freight_seller_state", "2017年各卖家州Olist运费排名", "M_OLIST_FREIGHT_VALUE", expected_dimension="D_OLIST_SELLER_STATE"),
        success("orders_total_2017", "2017年Olist订单量", "M_OLIST_ORDER_COUNT"),
        success("orders_month_2017", "2017年每月Olist订单数趋势", "M_OLIST_ORDER_COUNT", expected_dimension="D_MONTH", expected_chart="line"),
        success("orders_category", "2017年各商品品类Olist订单量", "M_OLIST_ORDER_COUNT", expected_dimension="D_OLIST_CATEGORY"),
        success("orders_customer_state", "2017年各客户州Olist订单量排名", "M_OLIST_ORDER_COUNT", expected_dimension="D_OLIST_CUSTOMER_STATE"),
        success("orders_seller_state", "2017年各卖家州Olist订单量", "M_OLIST_ORDER_COUNT", expected_dimension="D_OLIST_SELLER_STATE"),
        success("orders_status", "2017年各订单状态Olist订单数", "M_OLIST_ORDER_COUNT", expected_dimension="D_OLIST_ORDER_STATUS"),
        success("revenue_recent_three_months", "最近三个月Olist销售额", "M_OLIST_ITEM_REVENUE"),
        success("orders_recent_year", "最近一年Olist订单量", "M_OLIST_ORDER_COUNT"),
    ]
    cases += [
        {"name": f"clarify_{i}", "category": "ambiguity", "query": query, "domain": "auto", "expected_status": "CLARIFY", "must_not_compile": True}
        for i, query in enumerate(("Olist经营情况", "Olist业务表现", "看看Olist数据"), 1)
    ]
    cases += [
        {"name": f"reject_{i}", "category": "scope_boundary", "query": query, "domain": "auto", "expected_status": "REJECT", "must_not_compile": True}
        for i, query in enumerate((
            "商品成本、毛利额或毛利率是多少", "广告曝光、点击、投放费用或广告投产比", "库存余额或库存周转天数",
            "客户年龄、性别或其他人口属性", "预测未来销量、订单量或收入", "支付金额按商品品类拆分",
        ), 1)
    ]
    cases += [
        {"name": f"blocked_workspace_{i}", "category": "permission", "query": query, "domain": "auto", "workspace_id": "unauthorized", "expected_status": "BLOCKED", "must_not_compile": True}
        for i, query in enumerate(("2017年Olist销售额", "2017年Olist订单量", "2017年Olist运费"), 1)
    ]
    return cases


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(build())} cases to {OUTPUT}")
