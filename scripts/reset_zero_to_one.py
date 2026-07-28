"""Reset production_benchmark to a true persisted-state zero for 0→1 onboarding.

ClickHouse data and every evaluation file are read-only inputs and are never modified.
No semantic model, metric, join, alias, example, embedding, feedback, or query history
is recreated by this script.  Reconstruction must happen through public governance APIs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, func, select

from app.db.models import (
    BusinessDomain,
    ConversationContext,
    Dimension,
    EvidenceRecord,
    GoldenQuestion,
    Metric,
    MetricAlias,
    MetricDimension,
    MetricDraft,
    MetricEmbedding,
    MetricSemanticProfile,
    MetricVersion,
    ProductEvent,
    QueryRun,
    ReflectionValidation,
    ResultProfile,
    SemanticEntity,
    SemanticJoinDraft,
    SemanticJoinRelation,
    SemanticJoinVersion,
    SemanticModel,
    SemanticScopeExample,
    SemanticScopePolicy,
    UserFeedback,
    WarehouseSource,
)
from app.db.session import SessionLocal
from app.services.production_benchmark_semantics import DOMAIN_ID


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "data" / "evaluation"
REPORT_ROOT = ROOT / "reports" / "zero-to-one"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataset_inventory() -> dict:
    files = sorted(path for path in DATASET_ROOT.rglob("*") if path.is_file())
    return {
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "inventory_sha256": hashlib.sha256(
            "\n".join(f"{path.relative_to(ROOT)}:{sha256(path)}" for path in files).encode()
        ).hexdigest(),
    }


def current_counts(session) -> dict[str, int]:
    metric_ids = select(Metric.id).where(Metric.business_domain_id == DOMAIN_ID)
    return {
        "models": session.scalar(select(func.count()).select_from(SemanticModel).where(SemanticModel.business_domain_id == DOMAIN_ID)) or 0,
        "entities": session.scalar(select(func.count()).select_from(SemanticEntity).where(SemanticEntity.business_domain_id == DOMAIN_ID)) or 0,
        "joins": session.scalar(select(func.count()).select_from(SemanticJoinRelation).where(SemanticJoinRelation.business_domain_id == DOMAIN_ID)) or 0,
        "metrics": session.scalar(select(func.count()).select_from(Metric).where(Metric.business_domain_id == DOMAIN_ID)) or 0,
        "aliases": session.scalar(select(func.count()).select_from(MetricAlias).where(MetricAlias.metric_id.in_(metric_ids))) or 0,
        "embeddings": session.scalar(select(func.count()).select_from(MetricEmbedding).where(MetricEmbedding.metric_id.in_(metric_ids))) or 0,
        "feedback": session.scalar(select(func.count()).select_from(UserFeedback)) or 0,
        "golden_questions": session.scalar(select(func.count()).select_from(GoldenQuestion)) or 0,
        "query_runs": session.scalar(select(func.count()).select_from(QueryRun)) or 0,
        "conversation_contexts": session.scalar(select(func.count()).select_from(ConversationContext)) or 0,
        "warehouse_sources": session.scalar(select(func.count()).select_from(WarehouseSource).where(WarehouseSource.business_domain_id == DOMAIN_ID)) or 0,
    }


def reset() -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    deleted: dict[str, int] = {}
    with SessionLocal() as session:
        before = current_counts(session)
        metric_ids = list(session.scalars(select(Metric.id).where(Metric.business_domain_id == DOMAIN_ID)).all())
        relation_ids = list(session.scalars(select(SemanticJoinRelation.id).where(SemanticJoinRelation.business_domain_id == DOMAIN_ID)).all())
        model_ids = list(session.scalars(select(SemanticModel.id).where(SemanticModel.business_domain_id == DOMAIN_ID)).all())

        for model in (ReflectionValidation, EvidenceRecord, ResultProfile, GoldenQuestion, UserFeedback, ProductEvent, QueryRun, ConversationContext):
            result = session.execute(delete(model))
            deleted[f"{model.__table__.schema}.{model.__tablename__}"] = result.rowcount or 0

        if metric_ids:
            for model in (MetricDraft, MetricEmbedding, MetricAlias, MetricSemanticProfile, MetricDimension, MetricVersion):
                result = session.execute(delete(model).where(model.metric_id.in_(metric_ids)))
                deleted[f"metric_center.{model.__tablename__}"] = result.rowcount or 0
            deleted["metric_center.metric"] = session.execute(delete(Metric).where(Metric.id.in_(metric_ids))).rowcount or 0

        deleted["metric_center.semantic_scope_example"] = session.execute(delete(SemanticScopeExample).where(SemanticScopeExample.business_domain_id == DOMAIN_ID)).rowcount or 0
        deleted["metric_center.semantic_scope_policy"] = session.execute(delete(SemanticScopePolicy).where(SemanticScopePolicy.business_domain_id == DOMAIN_ID)).rowcount or 0
        if relation_ids:
            deleted["metric_center.semantic_join_version"] = session.execute(delete(SemanticJoinVersion).where(SemanticJoinVersion.relation_id.in_(relation_ids))).rowcount or 0
        deleted["metric_center.semantic_join_draft"] = session.execute(delete(SemanticJoinDraft).where(SemanticJoinDraft.business_domain_id == DOMAIN_ID)).rowcount or 0
        deleted["metric_center.semantic_join_relation"] = session.execute(delete(SemanticJoinRelation).where(SemanticJoinRelation.business_domain_id == DOMAIN_ID)).rowcount or 0
        deleted["metric_center.semantic_entity"] = session.execute(delete(SemanticEntity).where(SemanticEntity.business_domain_id == DOMAIN_ID)).rowcount or 0
        deleted["metric_center.semantic_model"] = session.execute(delete(SemanticModel).where(SemanticModel.business_domain_id == DOMAIN_ID)).rowcount or 0

        dimensions = session.scalars(select(Dimension)).all()
        removed_dimensions = 0
        changed_dimensions = 0
        for dimension in dimensions:
            mapping = dict(dimension.mapping_json or {})
            cleaned = {key: value for key, value in mapping.items() if key not in model_ids}
            if dimension.id.startswith("D_PROD_"):
                session.delete(dimension)
                removed_dimensions += 1
            elif cleaned != mapping:
                dimension.mapping_json = cleaned
                changed_dimensions += 1
        deleted["metric_center.dimension_deleted"] = removed_dimensions
        deleted["metric_center.dimension_mappings_cleaned"] = changed_dimensions

        deleted["metric_center.warehouse_source"] = session.execute(
            delete(WarehouseSource).where(
                (WarehouseSource.business_domain_id == DOMAIN_ID)
                | (WarehouseSource.id == "production_warehouse")
            )
        ).rowcount or 0
        # The domain is removed only after every governed child is gone.
        deleted["metric_center.business_domain"] = session.execute(delete(BusinessDomain).where(BusinessDomain.id == DOMAIN_ID)).rowcount or 0
        session.commit()
        after = current_counts(session)
    return before, deleted, after


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "ZERO_TO_ONE_RESET":
        raise RuntimeError("pass --confirm ZERO_TO_ONE_RESET")
    inventory_before = dataset_inventory()
    before, deleted, after = reset()
    inventory_after = dataset_inventory()
    valid = all(value == 0 for value in after.values()) and inventory_before == inventory_after
    result = {
        "reset_id": f"zero-to-one-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "generated_at": datetime.now(UTC).isoformat(),
        "domain": DOMAIN_ID,
        "protocol": "NO_SEED_NO_INDEX_NO_HISTORY",
        "before": before,
        "deleted": deleted,
        "after": after,
        "dataset_inventory_before": inventory_before,
        "dataset_inventory_after": inventory_after,
        "datasets_preserved": inventory_before == inventory_after,
        "valid": valid,
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / "reset-manifest.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
