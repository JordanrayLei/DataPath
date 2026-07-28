"""Remove governed runtime assets outside the retained production domain.

Evaluation datasets and warehouse tables are deliberately out of scope. The command
is a dry run unless the exact confirmation phrase is supplied.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select

from app.db.models import (
    BusinessDomain,
    Dimension,
    EvidenceRecord,
    Metric,
    MetricAlias,
    MetricDimension,
    MetricDraft,
    MetricEmbedding,
    MetricSemanticProfile,
    MetricVersion,
    SemanticEntity,
    SemanticJoinDraft,
    SemanticJoinRelation,
    SemanticJoinVersion,
    SemanticModel,
    SemanticScopeExample,
    SemanticScopePolicy,
    WarehouseSource,
)
from app.db.session import SessionLocal
from app.services.production_benchmark_semantics import DOMAIN_ID


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "zero-to-one" / "legacy-runtime-cleanup.json"
CONFIRMATION = "REMOVE_LEGACY_RUNTIME_ASSETS"


def inventory(session) -> dict:
    domains = list(
        session.scalars(select(BusinessDomain).order_by(BusinessDomain.id)).all()
    )
    return {
        "domains": [item.id for item in domains],
        "metrics_by_domain": {
            item.id: list(
                session.scalars(
                    select(Metric.id)
                    .where(Metric.business_domain_id == item.id)
                    .order_by(Metric.id)
                ).all()
            )
            for item in domains
        },
        "models_by_domain": {
            item.id: list(
                session.scalars(
                    select(SemanticModel.id)
                    .where(SemanticModel.business_domain_id == item.id)
                    .order_by(SemanticModel.id)
                ).all()
            )
            for item in domains
        },
        "joins_by_domain": {
            item.id: list(
                session.scalars(
                    select(SemanticJoinRelation.id)
                    .where(SemanticJoinRelation.business_domain_id == item.id)
                    .order_by(SemanticJoinRelation.id)
                ).all()
            )
            for item in domains
        },
    }


def cleanup(session, legacy_domain_ids: list[str]) -> dict[str, int]:
    deleted: dict[str, int] = {}
    metric_ids = list(
        session.scalars(
            select(Metric.id).where(Metric.business_domain_id.in_(legacy_domain_ids))
        ).all()
    )
    model_ids = list(
        session.scalars(
            select(SemanticModel.id).where(
                SemanticModel.business_domain_id.in_(legacy_domain_ids)
            )
        ).all()
    )
    relation_ids = list(
        session.scalars(
            select(SemanticJoinRelation.id).where(
                SemanticJoinRelation.business_domain_id.in_(legacy_domain_ids)
            )
        ).all()
    )

    if metric_ids:
        deleted["audit.evidence"] = session.execute(
            delete(EvidenceRecord).where(EvidenceRecord.metric_id.in_(metric_ids))
        ).rowcount or 0
        for model in (
            MetricDraft,
            MetricEmbedding,
            MetricAlias,
            MetricSemanticProfile,
            MetricDimension,
            MetricVersion,
        ):
            result = session.execute(delete(model).where(model.metric_id.in_(metric_ids)))
            deleted[f"metric_center.{model.__tablename__}"] = result.rowcount or 0
        deleted["metric_center.metric"] = session.execute(
            delete(Metric).where(Metric.id.in_(metric_ids))
        ).rowcount or 0

    deleted["metric_center.semantic_scope_example"] = session.execute(
        delete(SemanticScopeExample).where(
            SemanticScopeExample.business_domain_id.in_(legacy_domain_ids)
        )
    ).rowcount or 0
    deleted["metric_center.semantic_scope_policy"] = session.execute(
        delete(SemanticScopePolicy).where(
            SemanticScopePolicy.business_domain_id.in_(legacy_domain_ids)
        )
    ).rowcount or 0

    if relation_ids:
        deleted["metric_center.semantic_join_version"] = session.execute(
            delete(SemanticJoinVersion).where(
                SemanticJoinVersion.relation_id.in_(relation_ids)
            )
        ).rowcount or 0
    deleted["metric_center.semantic_join_draft"] = session.execute(
        delete(SemanticJoinDraft).where(
            SemanticJoinDraft.business_domain_id.in_(legacy_domain_ids)
        )
    ).rowcount or 0
    deleted["metric_center.semantic_join_relation"] = session.execute(
        delete(SemanticJoinRelation).where(
            SemanticJoinRelation.business_domain_id.in_(legacy_domain_ids)
        )
    ).rowcount or 0
    deleted["metric_center.semantic_entity"] = session.execute(
        delete(SemanticEntity).where(
            SemanticEntity.business_domain_id.in_(legacy_domain_ids)
        )
    ).rowcount or 0
    deleted["metric_center.semantic_model"] = session.execute(
        delete(SemanticModel).where(
            SemanticModel.business_domain_id.in_(legacy_domain_ids)
        )
    ).rowcount or 0

    retained_dimension_ids = set(session.scalars(select(MetricDimension.dimension_id)).all())
    removed_dimensions = 0
    changed_mappings = 0
    for dimension in session.scalars(select(Dimension)).all():
        mapping = dict(dimension.mapping_json or {})
        cleaned = {key: value for key, value in mapping.items() if key not in model_ids}
        if not cleaned and dimension.id not in retained_dimension_ids:
            session.delete(dimension)
            removed_dimensions += 1
        elif cleaned != mapping:
            dimension.mapping_json = cleaned
            changed_mappings += 1
    deleted["metric_center.dimension"] = removed_dimensions
    deleted["metric_center.dimension_mappings_cleaned"] = changed_mappings

    deleted["metric_center.warehouse_source"] = session.execute(
        delete(WarehouseSource).where(
            WarehouseSource.business_domain_id.in_(legacy_domain_ids)
        )
    ).rowcount or 0
    deleted["metric_center.business_domain"] = session.execute(
        delete(BusinessDomain).where(BusinessDomain.id.in_(legacy_domain_ids))
    ).rowcount or 0
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    with SessionLocal() as session:
        before = inventory(session)
        legacy_domain_ids = [
            domain_id for domain_id in before["domains"] if domain_id != DOMAIN_ID
        ]
        if args.confirm != CONFIRMATION:
            print(
                json.dumps(
                    {
                        "mode": "DRY_RUN",
                        "retained_domain": DOMAIN_ID,
                        "legacy_domains": legacy_domain_ids,
                        "before": before,
                        "confirmation": CONFIRMATION,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        deleted = cleanup(session, legacy_domain_ids)
        session.commit()
        after = inventory(session)

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "retained_domain": DOMAIN_ID,
        "legacy_domains_removed": legacy_domain_ids,
        "before": before,
        "deleted": deleted,
        "after": after,
        "valid": after["domains"] == [DOMAIN_ID]
        and len(after["metrics_by_domain"].get(DOMAIN_ID, [])) == 11,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
