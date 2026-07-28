from app.services.chatbi_entrypoint import build_query_dsl, resolve_time_range


def test_resolves_calendar_month_and_explicit_day_ranges() -> None:
    assert resolve_time_range("2024年2月订单量", {}) == {
        "start": "2024-02-01",
        "end": "2024-02-29",
    }
    assert resolve_time_range("2024年2月28日至3月1日订单量", {}) == {
        "start": "2024-02-28",
        "end": "2024-03-01",
    }
    assert resolve_time_range("2024年12月30日至12月31日订单量", {}) == {
        "start": "2024-12-30",
        "end": "2024-12-31",
    }


def build(query: str, context: dict | None = None) -> dict:
    return build_query_dsl(
        query,
        "production_benchmark",
        "M_PROD_ORDER_COUNT",
        1,
        "Asia/Shanghai",
        context or {},
    )


def test_builds_governed_filter_operators() -> None:
    equal = build("2024年币种为CNY的生产评测订单量")
    assert equal["dimensions"] == []
    assert equal["filters"] == [
        {"field_id": "D_PROD_CURRENCY", "operator": "eq", "values": ["CNY"]}
    ]
    not_in = build("2024年状态不属于completed、paid的生产评测订单量")
    assert not_in["dimensions"] == []
    assert not_in["filters"] == [
        {
            "field_id": "D_PROD_STATUS",
            "operator": "not_in",
            "values": ["completed", "paid"],
        }
    ]


def test_ranking_limit_and_month_dimension_change_are_explicit() -> None:
    assert build("2024年订单量按区域排名前5")["limit"] == 5
    dsl = build(
        "维度改成月份",
        {
            "dimensions": [{"dimension_id": "D_PROD_CURRENCY"}],
            "time_range": {"start": "2024-01-01", "end": "2024-12-31"},
        },
    )
    assert dsl["dimensions"] == [{"dimension_id": "D_MONTH"}]


def test_metric_switch_can_drop_incompatible_shape_but_keep_time() -> None:
    context = {
        "metrics": [{"metric_id": "M_PROD_ORDER_COUNT"}],
        "dimensions": [{"dimension_id": "D_MONTH"}],
        "filters": [
            {"field_id": "D_PROD_REGION", "operator": "eq", "values": ["east"]}
        ],
        "time_range": {"start": "2024-04-01", "end": "2024-06-30"},
        "intent": "trend_query",
    }
    dsl = build_query_dsl(
        "换成退款后净收入",
        "production_benchmark",
        "M_PROD_REFUND_ADJUSTED_REVENUE",
        3,
        "Asia/Shanghai",
        context,
        inherit_query_shape=False,
    )

    assert dsl["dimensions"] == []
    assert dsl["filters"] == []
    assert dsl["intent"] == "aggregate_query"
    assert dsl["time_range"] == {
        "start": "2024-04-01",
        "end": "2024-06-30",
        "timezone": "Asia/Shanghai",
    }
