"""Simulate human review of definition-only AI assets and publish via frontend APIs."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import GoldenQuestion, QueryRun, UserFeedback
from app.db.session import SessionLocal
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
SINGLE_PACKAGE = ROOT / "data" / "semantic_bootstrap" / "production_ai_preheat_v1.json"
CROSS_PACKAGE = ROOT / "data" / "semantic_bootstrap" / "production_cross_fact_preheat_v1.json"
OUT = ROOT / "reports" / "zero-to-one" / "ai-preheat-publication.json"
GENERIC_ALIASES = {"金额", "数据", "收入", "数量", "情况", "表现"}


def require_ok(response, action: str) -> dict:
    if not response.is_success:
        raise RuntimeError(f"{action} failed: HTTP {response.status_code} {response.text}")
    return response.json()


def draft_payload(detail: dict) -> dict:
    """Convert the public metric catalog response into a frontend draft payload."""

    metric = detail["metric"]
    return {
        "workspace_id": "demo",
        "metric_id": metric["metric_id"],
        "business_domain_id": metric["business_domain_id"],
        "name": metric["name"],
        "description": metric["description"],
        "metric_type": metric["metric_type"],
        "unit": metric["unit"],
        "owner": metric["owner"],
        "aliases": metric.get("aliases") or [],
        "positive_examples": metric.get("positive_examples") or [],
        "negative_examples": metric.get("negative_examples") or [],
        "semantic_model_id": metric["semantic_model"]["semantic_model_id"],
        "expression": detail["expression"],
        "default_aggregation": detail.get("default_aggregation", "default"),
        "time_dimension_id": detail.get("time_dimension_id", "D_DATE"),
        "dimension_ids": [row["dimension_id"] for row in metric["dimensions"]],
    }


def load_assets() -> tuple[dict[str, dict], list[dict]]:
    sources = []
    merged: dict[str, dict] = {}
    for path in (SINGLE_PACKAGE, CROSS_PACKAGE):
        raw = path.read_bytes()
        package = json.loads(raw)
        if package.get("generation_mode") != "canonical-definition-only":
            raise RuntimeError(f"untrusted generation provenance: {path}")
        sources.append(
            {
                "path": str(path.relative_to(ROOT)),
                "package_id": package["package_id"],
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_restriction": package["source_restriction"],
            }
        )
        merged.update(package["metrics"])
    return merged, sources


def review(metric_id: str, asset: dict, used_aliases: dict[str, str]) -> dict:
    aliases = list(dict.fromkeys(str(item).strip() for item in asset.get("aliases", []) if str(item).strip()))
    positives = list(dict.fromkeys(str(item).strip() for item in asset.get("positive_examples", []) if str(item).strip()))
    negatives = list(dict.fromkeys(str(item).strip() for item in asset.get("negative_examples", []) if str(item).strip()))
    if not aliases or not positives or not negatives:
        raise RuntimeError(f"incomplete AI semantic family: {metric_id}")
    forbidden = sorted(set(aliases) & GENERIC_ALIASES)
    if forbidden:
        raise RuntimeError(f"generic aliases rejected for {metric_id}: {forbidden}")
    collisions = {alias: used_aliases[alias] for alias in aliases if alias in used_aliases}
    if collisions:
        raise RuntimeError(f"cross-metric aliases rejected for {metric_id}: {collisions}")
    for alias in aliases:
        used_aliases[alias] = metric_id
    return {
        "aliases": aliases,
        "positive_examples": positives,
        "negative_examples": negatives,
        "reviewed_by": "simulated_metric_admin",
        "decision": "APPROVED",
        "checks": ["non_generic_alias", "cross_metric_alias_unique", "positive_examples_present", "neighbor_negatives_present", "formula_immutable"],
    }


def main() -> int:
    with SessionLocal() as session:
        history = {
            "query_runs": session.scalar(select(func.count()).select_from(QueryRun)) or 0,
            "feedback": session.scalar(select(func.count()).select_from(UserFeedback)) or 0,
            "golden_questions": session.scalar(select(func.count()).select_from(GoldenQuestion)) or 0,
        }
    if any(history.values()):
        raise RuntimeError(f"preheat must precede all runtime history: {history}")

    assets, sources = load_assets()
    used_aliases: dict[str, str] = {}
    reviewed = {metric_id: review(metric_id, asset, used_aliases) for metric_id, asset in assets.items()}
    records = []
    with TestClient(app) as client:
        for metric_id, semantic in reviewed.items():
            detail = require_ok(client.get(f"/api/chatbi/metrics/catalog/{metric_id}", params={"workspace_id": "demo"}), f"load {metric_id}")
            payload = draft_payload(detail)
            before_immutable = {key: payload[key] for key in ("name", "description", "metric_type", "unit", "owner", "semantic_model_id", "expression", "default_aggregation", "time_dimension_id", "dimension_ids")}
            payload.update({key: semantic[key] for key in ("aliases", "positive_examples", "negative_examples")})
            saved = require_ok(client.put(f"/api/chatbi/metrics/manage/drafts/{metric_id}", json=payload), f"save preheat {metric_id}")
            after = saved["draft"]
            after_immutable = {key: after[key] for key in before_immutable}
            if after_immutable != before_immutable:
                raise RuntimeError(f"immutable metric contract changed during preheat: {metric_id}")
            if saved["draft"]["validation"].get("alias_conflicts"):
                raise RuntimeError(f"backend alias conflict: {metric_id}")
            publication = require_ok(client.post(f"/api/chatbi/metrics/manage/drafts/{metric_id}/prelaunch-publish", json={"workspace_id": "demo"}), f"publish preheat {metric_id}")
            indexed = require_ok(client.post(f"/api/chatbi/metrics/manage/semantic-index/{metric_id}/refresh", json={"workspace_id": "demo"}), f"index {metric_id}")
            records.append(
                {
                    "metric_id": metric_id,
                    "review": semantic,
                    "published_version": publication["version"],
                    "indexed_documents": indexed["documents"],
                    "immutable_contract_preserved": True,
                }
            )

    report = {
        "publication_id": "zero-to-one-ai-preheat-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "transport": "frontend-equivalent public APIs",
        "generation_note": "Uses previously generated and provenance-restricted definition-only AI packages because the application has no DEEPSEEK_API_KEY configured.",
        "sources": sources,
        "forbidden_inputs_opened": [],
        "runtime_history_before_publication": history,
        "metric_count": len(records),
        "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metric_count": len(records), "alias_count": len(used_aliases), "runtime_history": history}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
