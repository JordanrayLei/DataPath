from __future__ import annotations

from scripts.import_golden_badcases import classify_badcase


def test_badcase_classification_routes_to_actionable_owners() -> None:
    semantic = classify_badcase(
        {"category": "semantic_robustness", "expected_status": "SUCCESS", "observed_status": "REJECT"}
    )
    ambiguity = classify_badcase(
        {"category": "ambiguity", "expected_status": "CLARIFY", "observed_status": "REJECT"}
    )
    safety = classify_badcase(
        {"category": "scope_and_safety", "expected_status": "BLOCKED", "observed_status": "REJECT"}
    )
    assert semantic["cluster"] == "retrieval_recall"
    assert semantic["owner"] == "AI_RETRIEVAL"
    assert ambiguity["cluster"] == "ambiguity_gate"
    assert ambiguity["owner"] == "QUERY_UNDERSTANDING"
    assert safety["cluster"] == "safety_action_classification"
    assert safety["owner"] == "SAFETY_GATE"
