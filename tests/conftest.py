from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from scripts.seed_metric_center import seed


@pytest.fixture(scope="session", autouse=True)
def seeded_metric_center() -> None:
    seed()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def service_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {get_settings().chatbi_api_token}",
        "X-Request-ID": "req_test_001",
        "X-Trace-ID": "trace_test_001",
    }


def preprocess(metric_mentions: list[str]) -> dict:
    return {
        "normalized_query": "测试查询",
        "metric_mentions": metric_mentions,
        "dimension_mentions": [],
        "filter_mentions": [],
        "time_text": "最近一年",
        "time_start": "2025-07-01",
        "time_end": "2026-06-30",
        "comparison": "",
        "inherit_context": False,
    }
