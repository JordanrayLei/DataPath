from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.schemas.chatbi import SemanticScopeExampleInput, SemanticScopeExampleItem
from app.services.semantic_scope_management import (
    SemanticScopeManagementError,
    normalize_scope_examples,
)


def test_scope_examples_are_normalized_and_deduplicated() -> None:
    normalized = normalize_scope_examples(
        [
            SemanticScopeExampleInput(text="  员工   离职率。 ", reason=" 人力资源 主题 "),
            SemanticScopeExampleInput(text="员工 离职率", reason="重复"),
            SemanticScopeExampleInput(text="服务器 CPU 使用率", reason="基础设施"),
            SemanticScopeExampleInput(text="天气预报", reason="公共信息"),
        ]
    )

    assert [item.text for item in normalized] == [
        "员工 离职率",
        "服务器 CPU 使用率",
        "天气预报",
    ]
    assert normalized[0].reason == "人力资源 主题"


def test_scope_examples_require_three_unique_semantic_boundaries() -> None:
    with pytest.raises(SemanticScopeManagementError):
        normalize_scope_examples(
            [
                SemanticScopeExampleInput(text="天气预报"),
                SemanticScopeExampleInput(text="天气预报。"),
                SemanticScopeExampleInput(text="员工离职率"),
            ]
        )


def test_specificity_boundary_is_a_supported_frontend_item() -> None:
    item = SemanticScopeExampleItem(
        id=1,
        business_domain_id="production_benchmark",
        text="明确询问支付到账金额",
        label="SPECIFIC",
        reason="明确金额方向",
        is_active=True,
        embedding_model="test-model",
        created_at=datetime.now(UTC),
    )
    assert item.label == "SPECIFIC"


def test_scope_management_api_exposes_frontend_editable_collection(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = {}

    def fake_replace(session, domain, payload, request_id, trace_id):
        captured["domain"] = domain
        captured["examples"] = [item.model_dump() for item in payload.examples]
        return {
            "request_id": request_id,
            "trace_id": trace_id,
            "status": "SUCCESS",
            "business_domain_id": domain,
            "items": [
                {
                    "id": index,
                    "business_domain_id": domain,
                    "text": item.text,
                    "label": "OUT_OF_SCOPE",
                    "reason": item.reason,
                    "is_active": True,
                    "embedding_model": "test-model",
                    "created_at": datetime.now(UTC),
                }
                for index, item in enumerate(payload.examples, 1)
            ],
            "total": len(payload.examples),
            "embedding_model": "test-model",
            "total_tokens": 12,
            "negative_threshold": payload.negative_threshold,
            "margin": payload.margin,
        }

    monkeypatch.setattr("app.api.routes.chatbi.replace_scope_examples", fake_replace)
    response = client.put(
        "/api/chatbi/metrics/manage/scope-examples/production_benchmark",
        json={
            "workspace_id": "demo",
            "examples": [
                {"text": "员工离职率", "reason": "人力资源"},
                {"text": "服务器使用率", "reason": "基础设施"},
                {"text": "天气预报", "reason": "公共信息"},
            ],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["total"] == 3
    assert captured["domain"] == "production_benchmark"
    assert captured["examples"][0]["reason"] == "人力资源"
    assert response.json()["negative_threshold"] == 0.64
