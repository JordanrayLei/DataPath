from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from scripts.seed_production_benchmark import seed


def test_join_graph_governance_publish_flow() -> None:
    seed()
    relation_id = "J_PROD_SHIPMENTS_WAREHOUSE"
    payload = {
        "workspace_id": "demo",
        "left_entity_id": "E_PROD_SHIPMENTS",
        "right_entity_id": "E_PROD_WAREHOUSE",
        "left_keys": ["warehouse_sk"],
        "right_keys": ["warehouse_sk"],
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
        response = client.post("/api/chatbi/join-graph/scan?domain=production_benchmark")
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    candidates = response.json()["candidates"]
    assert any(
        item["left_entity_id"] == "E_PROD_SHIPMENTS"
        and item["right_entity_id"] == "E_PROD_WAREHOUSE"
        and item["left_keys"] == ["warehouse_sk"]
        for item in candidates
    )
