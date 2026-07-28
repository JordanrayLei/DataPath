from __future__ import annotations

import pytest

from app.services.chatbi_entrypoint import resolve_time_range


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("2024年第一季度订单量", {"start": "2024-01-01", "end": "2024-03-31"}),
        ("2024年第二季度支付实收金额", {"start": "2024-04-01", "end": "2024-06-30"}),
        ("2024年前九个月退款金额", {"start": "2024-01-01", "end": "2024-09-30"}),
        ("2024年前3个月订单量", {"start": "2024-01-01", "end": "2024-03-31"}),
        ("2024年商品净收入", {"start": "2024-01-01", "end": "2024-12-31"}),
        ("最近三个月支付实收金额", {"start": "2024-10-01", "end": "2024-12-31"}),
        ("最近一年订单量", {"start": "2024-01-01", "end": "2024-12-31"}),
    ],
)
def test_resolve_time_range_prioritizes_specific_periods(
    query: str, expected: dict[str, str]
) -> None:
    assert resolve_time_range(query, {}) == expected


def test_resolve_time_range_inherits_context_without_explicit_period() -> None:
    previous = {"time_range": {"start": "2024-04-01", "end": "2024-06-30"}}
    assert resolve_time_range("换成退款金额", previous) == previous["time_range"]
