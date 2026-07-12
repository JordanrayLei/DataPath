from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from scripts.seed_olist_staging import seed


def test_join_graph_governance_publish_flow() -> None:
    seed()
    relation_id = "J_OLIST_ITEMS_PRODUCTS"
    payload = {
        "workspace_id": "demo",
        "left_entity_id": "E_OLIST_ORDER_ITEMS",
        "right_entity_id": "E_OLIST_PRODUCTS",
        "left_keys": ["product_id"],
        "right_keys": ["product_id"],
        "relationship_type": "many_to_one",
        "join_type": "left",
        "fanout_strategy": "safe",
        "priority": 20,
    }
    with TestClient(app) as client:
        saved = client.put(f"/api/chatbi/join-graph/drafts/{relation_id}", json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()["status"] == "DRAFT"

        validated = client.post(f"/api/chatbi/join-graph/drafts/{relation_id}/validate")
        assert validated.status_code == 200, validated.text
        checks = validated.json()["validation"]
        assert checks["safe_to_publish"] is True
        assert checks["right_key_unique_rate"] == 1
        assert checks["fanout_multiplier"] <= 1.001

        published = client.post(f"/api/chatbi/join-graph/drafts/{relation_id}/publish")
        assert published.status_code == 200, published.text
        assert published.json()["status"] == "PUBLISHED"
        published_version = published.json()["version"]
        assert published_version >= 2

        graph = client.get("/api/chatbi/join-graph")
        assert graph.status_code == 200
        relation = next(item for item in graph.json()["relations"] if item["id"] == relation_id)
        assert relation["status"] == "PUBLISHED"
        assert relation["version"] == published_version


def test_join_candidate_scan_only_creates_suggestions() -> None:
    with TestClient(app) as client:
        response = client.post("/api/chatbi/join-graph/scan?domain=sales")
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    candidates = response.json()["candidates"]
    assert any(
        item["left_entity_id"] == "E_OLIST_ORDER_ITEMS"
        and item["right_entity_id"] == "E_OLIST_PRODUCTS"
        and item["left_keys"] == ["product_id"]
        for item in candidates
    )
