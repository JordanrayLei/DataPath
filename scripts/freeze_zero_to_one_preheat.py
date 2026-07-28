"""Freeze zero-to-one semantics before opening any evaluation case file."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.db.models import (
    GoldenQuestion,
    Metric,
    MetricAlias,
    MetricEmbedding,
    MetricSemanticProfile,
    QueryRun,
    SemanticJoinRelation,
    SemanticModel,
    UserFeedback,
)
from app.db.session import SessionLocal
from scripts.zero_to_one_evaluation_utils import (
    product_code_sha256,
    semantic_assets_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports" / "zero-to-one"
OUT = REPORT_ROOT / "preheat-freeze.json"
DOMAIN = "production_benchmark"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with SessionLocal() as session:
        metric_ids = list(session.scalars(select(Metric.id).where(Metric.business_domain_id == DOMAIN, Metric.status == "PUBLISHED")).all())
        counts = {
            "models": session.scalar(select(func.count()).select_from(SemanticModel).where(SemanticModel.business_domain_id == DOMAIN, SemanticModel.status == "ACTIVE")) or 0,
            "published_joins": session.scalar(select(func.count()).select_from(SemanticJoinRelation).where(SemanticJoinRelation.business_domain_id == DOMAIN, SemanticJoinRelation.status == "PUBLISHED")) or 0,
            "published_metrics": len(metric_ids),
            "aliases": session.scalar(select(func.count()).select_from(MetricAlias).where(MetricAlias.metric_id.in_(metric_ids))) or 0,
            "semantic_profiles": session.scalar(select(func.count()).select_from(MetricSemanticProfile).where(MetricSemanticProfile.metric_id.in_(metric_ids))) or 0,
            "embeddings": session.scalar(select(func.count()).select_from(MetricEmbedding).where(MetricEmbedding.metric_id.in_(metric_ids), MetricEmbedding.is_active.is_(True))) or 0,
            "query_runs": session.scalar(select(func.count()).select_from(QueryRun)) or 0,
            "feedback": session.scalar(select(func.count()).select_from(UserFeedback)) or 0,
            "golden_questions": session.scalar(select(func.count()).select_from(GoldenQuestion)) or 0,
        }
    expected = {"models": 11, "published_joins": 6, "published_metrics": 11, "aliases": 62, "semantic_profiles": 11, "query_runs": 0, "feedback": 0, "golden_questions": 0}
    violations = {key: {"expected": value, "actual": counts[key]} for key, value in expected.items() if counts[key] != value}
    report = {
        "freeze_id": "zero-to-one-preheat-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "business_domain": DOMAIN,
        "semantic_assets_sha256": semantic_assets_sha256(DOMAIN),
        "product_code_sha256": product_code_sha256(),
        "human_governance_report_sha256": file_sha256(REPORT_ROOT / "human-governance-publication.json"),
        "ai_preheat_report_sha256": file_sha256(REPORT_ROOT / "ai-preheat-publication.json"),
        "counts": counts,
        "evaluation_case_files_opened_before_freeze": [],
        "violations": violations,
        "valid": not violations,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
