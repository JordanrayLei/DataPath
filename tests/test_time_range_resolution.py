from __future__ import annotations

import pytest

from app.services.chatbi_entrypoint import resolve_time_range


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("2017年第一季度Olist销售额", {"start": "2017-01-01", "end": "2017-03-31"}),
        ("2017年第二季度Olist销售额", {"start": "2017-04-01", "end": "2017-06-30"}),
        ("2018年前九个月Olist销售额", {"start": "2018-01-01", "end": "2018-09-30"}),
        ("2018年前3个月Olist订单量", {"start": "2018-01-01", "end": "2018-03-31"}),
        ("2018年Olist销售额", {"start": "2018-01-01", "end": "2018-12-31"}),
        ("最近三个月Olist销售额", {"start": "2018-07-01", "end": "2018-09-30"}),
        ("最近一年Olist订单量", {"start": "2017-10-01", "end": "2018-09-30"}),
    ],
)
def test_resolve_time_range_prioritizes_specific_periods(
    query: str, expected: dict[str, str]
) -> None:
    assert resolve_time_range(query, {}) == expected


def test_resolve_time_range_inherits_context_without_explicit_period() -> None:
    previous = {"time_range": {"start": "2017-04-01", "end": "2017-06-30"}}
    assert resolve_time_range("换成Olist运费", previous) == previous["time_range"]
