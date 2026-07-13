from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "evaluation" / "golden"


def load_split(name: str) -> list[dict]:
    return json.loads((GOLDEN / f"olist_golden_{name}.json").read_text(encoding="utf-8"))


def test_golden_dataset_is_complete_stratified_and_leak_free() -> None:
    splits = {name: load_split(name) for name in ("development", "regression", "blind")}
    assert {name: len(items) for name, items in splits.items()} == {
        "development": 220, "regression": 80, "blind": 60
    }
    all_cases = [case for items in splits.values() for case in items]
    assert len(all_cases) == 360
    assert len({case["case_id"] for case in all_cases}) == 360
    assert Counter(case["category"] for case in all_cases) == {
        "core_metric": 100, "multi_entity": 100, "semantic_robustness": 30,
        "ambiguity": 20, "multi_turn": 40, "scope_and_safety": 35,
        "permission": 15, "data_edge": 20,
    }
    queries = {name: {case["query"] for case in items} for name, items in splits.items()}
    assert not queries["development"] & queries["regression"]
    assert not queries["development"] & queries["blind"]
    assert not queries["regression"] & queries["blind"]


def test_success_oracles_and_failure_guards_are_present() -> None:
    cases = sum((load_split(name) for name in ("development", "regression", "blind")), [])
    for case in cases:
        assert case["query"].strip()
        assert case["split"] in {"development", "regression", "blind"}
        if case["expected_status"] == "SUCCESS" and case["category"] != "multi_turn":
            oracle = case["result_assertions"]
            assert len(oracle["result_checksum_sha256"]) == 64
            assert len(oracle["canonical_sql_sha256"]) == 64
            assert oracle["row_count"] >= 1
            assert case["expected_metric_id"].startswith("M_OLIST_")
            assert case["must_not_leak_sql"] is True
        if case["expected_status"] in {"REJECT", "BLOCKED"}:
            assert case["must_not_compile"] is True
            assert case["must_not_execute"] is True


def test_snapshot_manifest_covers_all_olist_tables() -> None:
    manifest = json.loads((GOLDEN / "olist_golden_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["table_row_counts"]) == 9
    assert all(value > 0 for value in manifest["table_row_counts"].values())
    assert manifest["split_distribution"] == {"development": 220, "regression": 80, "blind": 60}
