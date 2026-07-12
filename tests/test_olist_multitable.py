from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.join_planner import JoinPlanningError, plan_query_models
from app.db.session import SessionLocal
from scripts.seed_olist_staging import seed as seed_olist


@pytest.fixture(scope="module", autouse=True)
def olist_semantic_graph() -> None:
    seed_olist()


@pytest.mark.parametrize(
    ("query", "metric_id", "dimension_id", "tables"),
    [
        (
            "2017年各商品品类Olist销售额排名",
            "M_OLIST_ITEM_REVENUE",
            "D_OLIST_CATEGORY",
            {
                "data_warehouse.olist_order_items",
                "data_warehouse.olist_orders",
                "data_warehouse.olist_products",
                "data_warehouse.olist_product_category_translation",
            },
        ),
        (
            "2017年各客户州Olist订单量排名",
            "M_OLIST_ORDER_COUNT",
            "D_OLIST_CUSTOMER_STATE",
            {
                "data_warehouse.olist_order_items",
                "data_warehouse.olist_orders",
                "data_warehouse.olist_customers",
            },
        ),
        (
            "2017年各卖家州Olist运费排名",
            "M_OLIST_FREIGHT_VALUE",
            "D_OLIST_SELLER_STATE",
            {
                "data_warehouse.olist_order_items",
                "data_warehouse.olist_orders",
                "data_warehouse.olist_sellers",
            },
        ),
    ],
)
def test_olist_multi_entity_entrypoint(
    query: str,
    metric_id: str,
    dimension_id: str,
    tables: set[str],
) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/chatbi/ask",
            json={
                "query": query,
                "workspace_id": "demo",
                "conversation_id": f"olist_{metric_id}_{dimension_id}",
                "biz_domain": "auto",
                "timezone": "Asia/Shanghai",
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "SUCCESS", body
    assert body["selected_metric"]["metric_id"] == metric_id
    assert body["dsl"]["dsl_version"] == "2.0"
    assert body["dsl"]["query_mode"] == "multi_entity"
    assert body["dsl"]["dimensions"][0]["dimension_id"] == dimension_id
    assert set(body["compiled"]["lineage"]["tables"]) == tables
    assert body["execution"]["row_count"] > 0
    assert body["reflection"]["status"] == "PASS"
    assert "SELECT " not in str(body).upper()
    assert any(step["key"] == "route" for step in body["steps"])


def test_planner_rejects_unpublished_fact_to_fact_path() -> None:
    with SessionLocal() as session:
        with pytest.raises(
            JoinPlanningError,
            match="not an active join entity|no published safe join path",
        ):
            plan_query_models(
                session,
                "SM_OLIST_ORDER_ITEMS",
                {"SM_OLIST_PAYMENTS"},
            )
