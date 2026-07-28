from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Callable

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import MetricDraft, SemanticModel
from app.schemas.governance import MetricPreheatApplyRequest
from app.services.metric_catalog import alias_conflicts, semantic_readiness


class MetricPreheatError(ValueError):
    pass


def _canonical_metadata(session: Session, draft: MetricDraft) -> dict[str, Any]:
    model = session.get(SemanticModel, draft.semantic_model_id)
    return {
        "metric_id": draft.metric_id,
        "name": draft.name,
        "business_domain_id": draft.business_domain_id,
        "business_definition": draft.description,
        "metric_type": draft.metric_type,
        "unit": draft.unit,
        "formula": draft.expression_json,
        "primary_semantic_model": draft.semantic_model_id,
        "physical_table": model.physical_table if model else "",
        "available_fields": list(model.fields_json or []) if model else [],
        "dimensions": list(draft.dimension_ids_json or []),
        "existing_aliases": list(draft.aliases_json or []),
        "existing_positive_examples": list(draft.positive_examples_json or []),
        "existing_negative_examples": list(draft.negative_examples_json or []),
    }


def _call_deepseek(metadata: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise MetricPreheatError("DEEPSEEK_API_KEY is not configured")
    prompt = (
        "你是企业数据指标语义治理助手。只根据给定、已经由人员确认的业务元数据，"
        "生成用于自然语言检索的语义预热草稿。不得修改公式、维度、血缘或业务定义，"
        "不得杜撰字段。输出严格 JSON：aliases 5-12 条、positive_examples 8-20 条、"
        "negative_examples 5-12 条。负例应是容易混淆但不应命中该指标的问法。\n"
        + json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    )
    try:
        with httpx.Client(timeout=45, trust_env=False) as client:
            response = client.post(
                settings.deepseek_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json={
                    "model": settings.deepseek_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise MetricPreheatError(f"AI preheat generation failed: {error}") from error


def _clean_list(value: Any, maximum: int) -> list[str]:
    if not isinstance(value, list):
        raise MetricPreheatError("AI response lists are invalid")
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if any(len(item) > 200 for item in cleaned):
        raise MetricPreheatError("AI response contains an overlong item")
    return list(dict.fromkeys(cleaned))[:maximum]


def generate_preheat_proposal(
    session: Session,
    metric_id: str,
    *,
    generator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    draft = session.query(MetricDraft).filter(MetricDraft.metric_id == metric_id).one_or_none()
    if draft is None:
        raise MetricPreheatError("save the metric draft before generating preheat semantics")
    metadata = _canonical_metadata(session, draft)
    canonical = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    generated = (generator or _call_deepseek)(metadata)
    proposal = {
        "status": "PROPOSED",
        "source": "approved_metric_metadata_only",
        "source_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
        "model": get_settings().deepseek_model,
        "aliases": _clean_list(generated.get("aliases"), 30),
        "positive_examples": _clean_list(generated.get("positive_examples"), 80),
        "negative_examples": _clean_list(generated.get("negative_examples"), 80),
        "human_review_required": True,
        "changes_formula_or_lineage": False,
    }
    validation = dict(draft.validation_json or {})
    validation["ai_preheat_proposal"] = proposal
    validation["semantic_readiness"] = semantic_readiness(
        description=draft.description,
        owner=draft.owner,
        aliases=draft.aliases_json,
        positive_examples=draft.positive_examples_json,
        negative_examples=draft.negative_examples_json,
    )
    validation["alias_conflicts"] = alias_conflicts(
        session,
        metric_id=draft.metric_id,
        business_domain_id=draft.business_domain_id,
        name=draft.name,
        aliases=draft.aliases_json,
    )
    draft.validation_json = validation
    session.commit()
    return proposal


def apply_preheat_proposal(
    session: Session, metric_id: str, payload: MetricPreheatApplyRequest
) -> dict[str, Any]:
    draft = session.query(MetricDraft).filter(MetricDraft.metric_id == metric_id).one_or_none()
    if draft is None:
        raise MetricPreheatError("metric draft does not exist")
    proposal = dict((draft.validation_json or {}).get("ai_preheat_proposal") or {})
    if proposal.get("status") != "PROPOSED":
        raise MetricPreheatError("generate a preheat proposal before applying it")
    draft.aliases_json = list(dict.fromkeys(payload.aliases))
    draft.positive_examples_json = list(dict.fromkeys(payload.positive_examples))
    draft.negative_examples_json = list(dict.fromkeys(payload.negative_examples))
    proposal.update(
        {
            "status": "HUMAN_APPLIED",
            "reviewed_by": payload.operator_id,
            "reviewed_at": datetime.now(UTC).isoformat(),
        }
    )
    validation = dict(draft.validation_json or {})
    validation["ai_preheat_proposal"] = proposal
    validation["semantic_readiness"] = semantic_readiness(
        description=draft.description,
        owner=draft.owner,
        aliases=draft.aliases_json,
        positive_examples=draft.positive_examples_json,
        negative_examples=draft.negative_examples_json,
    )
    validation["alias_conflicts"] = alias_conflicts(
        session,
        metric_id=draft.metric_id,
        business_domain_id=draft.business_domain_id,
        name=draft.name,
        aliases=draft.aliases_json,
    )
    draft.validation_json = validation
    session.commit()
    return proposal
