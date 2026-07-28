from __future__ import annotations

from app.services.production_benchmark_semantics import (
    CROSS_FACT_METRICS,
    MODEL_FIELDS,
    MODEL_TABLES,
    PUBLISHED_METRICS,
    RELATIONS,
)
from scripts.build_production_like_warehouse import _contract, table_columns


def test_semantic_models_reference_real_contract_tables_and_fields() -> None:
    tables = {table["name"]: table for table in _contract()["tables"]}
    assert len(MODEL_TABLES) == 11
    for model_id, physical_table in MODEL_TABLES.items():
        table_name = physical_table.split(".", 1)[1]
        assert table_name in tables
        actual_fields = {name for name, _ in table_columns(tables[table_name])}
        assert MODEL_FIELDS[model_id] <= actual_fields


def test_only_single_fact_metrics_are_published() -> None:
    assert len(PUBLISHED_METRICS) == 9
    assert len(CROSS_FACT_METRICS) == 2
    assert all("source_model_id" not in str(metric[5]) for metric in PUBLISHED_METRICS)


def test_advanced_join_paths_remain_staged() -> None:
    published = [relation for relation in RELATIONS.values() if relation[-1] == "PUBLISHED"]
    staged = [relation for relation in RELATIONS.values() if relation[-1] == "STAGED"]
    assert len(published) == 6
    assert len(staged) == 4
    assert all(relation[-2] == "safe" for relation in published)
    assert all(relation[-2] == "as_of_scd2" for relation in staged)
