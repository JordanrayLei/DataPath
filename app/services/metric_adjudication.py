from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Metric, MetricVersion
from app.schemas.chatbi import (
    MetricAdjudicationDecision,
    MetricAdjudicationValidateRequest,
    MetricMentionDecision,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
)
from app.services.signing import sign_value


class MetricAdjudicationError(RuntimeError):
    pass


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _query_hash(query: str, normalized_query: str) -> str:
    return hashlib.sha256(f"{query}\n{normalized_query}".encode()).hexdigest()


def _candidate_manifest(retrieval: MetricRetrieveResponse) -> list[dict[str, Any]]:
    return [
        {
            "mention_index": mention_index,
            "metric_id": candidate.metric_id,
            "metric_version": candidate.metric_version,
        }
        for mention_index, mention in enumerate(retrieval.mentions)
        for candidate in mention.candidates
    ]


def issue_adjudication_token(
    request: MetricRetrieveRequest,
    retrieval: MetricRetrieveResponse,
) -> str:
    settings = get_settings()
    claims = {
        "exp": int(time.time()) + settings.metric_adjudication_token_ttl_seconds,
        "workspace_id": request.workspace_id,
        "operator_id": request.operator_id,
        "biz_domain": request.biz_domain,
        "query_hash": _query_hash(request.query, request.normalized_query),
        "retrieval_request_id": retrieval.request_id,
        "gate_status": retrieval.gate_status,
        "candidates": _candidate_manifest(retrieval),
    }
    encoded = _b64encode(
        json.dumps(claims, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    return f"mat.v1.{encoded}.{sign_value(encoded, settings.signing_secret)}"


def _verify_token(payload: MetricAdjudicationValidateRequest) -> dict[str, Any]:
    try:
        prefix, version, encoded, signature = payload.adjudication_token.split(".", 3)
        if (prefix, version) != ("mat", "v1"):
            raise ValueError("unsupported token version")
        expected = sign_value(encoded, get_settings().signing_secret)
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(_b64decode(encoded))
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise MetricAdjudicationError("ADJUDICATION_TOKEN_INVALID") from error

    if int(claims.get("exp", 0)) < int(time.time()):
        raise MetricAdjudicationError("ADJUDICATION_TOKEN_EXPIRED")
    expected_context = (
        payload.workspace_id,
        payload.operator_id,
        payload.biz_domain,
        _query_hash(payload.query, payload.normalized_query),
        payload.retrieval.request_id,
        payload.retrieval.gate_status,
    )
    actual_context = (
        claims.get("workspace_id"),
        claims.get("operator_id"),
        claims.get("biz_domain"),
        claims.get("query_hash"),
        claims.get("retrieval_request_id"),
        claims.get("gate_status"),
    )
    if actual_context != expected_context:
        raise MetricAdjudicationError("ADJUDICATION_CONTEXT_MISMATCH")
    if claims.get("candidates") != _candidate_manifest(payload.retrieval):
        raise MetricAdjudicationError("ADJUDICATION_CANDIDATES_TAMPERED")
    return claims


def _candidate_is_currently_published(
    session: Session,
    domain: str,
    metric_id: str,
    metric_version: int,
) -> bool:
    latest_version = session.scalar(
        select(MetricVersion.version)
        .join(Metric, Metric.id == MetricVersion.metric_id)
        .where(
            Metric.id == metric_id,
            Metric.business_domain_id == domain,
            Metric.status == "PUBLISHED",
            MetricVersion.status == "PUBLISHED",
        )
        .order_by(MetricVersion.version.desc())
        .limit(1)
    )
    return latest_version == metric_version


def _fail_closed(
    retrieval: MetricRetrieveResponse,
    reason_code: str,
) -> MetricRetrieveResponse:
    mentions = [
        mention.model_copy(
            update={"selected_metric_id": "", "selected_metric_version": None}
        )
        for mention in retrieval.mentions
    ]
    return retrieval.model_copy(
        update={
            "gate_status": "CLARIFY",
            "mentions": mentions,
            "reason_codes": [reason_code],
            "clarification_message": "请选择正确的指标口径。",
            "runtime_diagnostics": {
                **retrieval.runtime_diagnostics,
                "metric_adjudication": {
                    "validated": False,
                    "reason_code": reason_code,
                },
            },
            "adjudication_token": "",
        }
    )


def _validate_success(
    session: Session,
    domain: str,
    mention: MetricMentionDecision,
    decision: MetricAdjudicationDecision,
) -> MetricMentionDecision | None:
    settings = get_settings()
    candidate = next(
        (item for item in mention.candidates if item.metric_id == decision.selected_metric_id),
        None,
    )
    if (
        candidate is None
        or not candidate.authorized
        or decision.confidence < settings.metric_judge_min_confidence
        or not _candidate_is_currently_published(
            session,
            domain,
            candidate.metric_id,
            candidate.metric_version,
        )
    ):
        return None
    return mention.model_copy(
        update={
            "selected_metric_id": candidate.metric_id,
            "selected_metric_version": candidate.metric_version,
            "probability": decision.confidence,
        }
    )


def validate_dify_metric_adjudication(
    session: Session,
    payload: MetricAdjudicationValidateRequest,
) -> MetricRetrieveResponse:
    """Validate Dify's AI decision without allowing it to alter metric semantics."""

    try:
        _verify_token(payload)
    except MetricAdjudicationError as error:
        return _fail_closed(payload.retrieval, str(error))

    if payload.retrieval.gate_status not in {"LLM_DISAMBIGUATE", "CLARIFY"}:
        return _fail_closed(payload.retrieval, "ADJUDICATION_GATE_NOT_ELIGIBLE")
    indexed = {item.mention_index: item for item in payload.decisions}
    if len(indexed) != len(payload.decisions) or set(indexed) != set(range(len(payload.retrieval.mentions))):
        return _fail_closed(payload.retrieval, "ADJUDICATION_DECISIONS_INCOMPLETE")

    mentions: list[MetricMentionDecision] = []
    states: list[str] = []
    clarification = ""
    reason_codes: list[str] = []
    for index, mention in enumerate(payload.retrieval.mentions):
        decision = indexed[index]
        reason_codes.append(f"METRIC_JUDGE_{decision.reason_code}")
        if decision.decision == "SUCCESS":
            resolved = _validate_success(session, payload.biz_domain, mention, decision)
            if resolved is None:
                return _fail_closed(
                    payload.retrieval,
                    "ADJUDICATION_INVALID_OR_LOW_CONFIDENCE_SUCCESS",
                )
            mentions.append(resolved)
            states.append("PASS")
        else:
            mentions.append(
                mention.model_copy(
                    update={"selected_metric_id": "", "selected_metric_version": None}
                )
            )
            states.append(decision.decision)
            clarification = decision.clarification_question or clarification

    if "REJECT" in states:
        gate_status = "REJECT"
    elif states and all(item == "PASS" for item in states):
        gate_status = "PASS"
    else:
        gate_status = "CLARIFY"
    return payload.retrieval.model_copy(
        update={
            "gate_status": gate_status,
            "mentions": mentions,
            "reason_codes": reason_codes,
            "clarification_message": (
                clarification or "请选择正确的指标口径。"
                if gate_status == "CLARIFY"
                else ""
            ),
            "runtime_diagnostics": {
                **payload.retrieval.runtime_diagnostics,
                "metric_adjudication": {
                    "validated": True,
                    "provider": "dify_deepseek",
                    "min_confidence": get_settings().metric_judge_min_confidence,
                    "decisions": [
                        {
                            "mention_index": item.mention_index,
                            "decision": item.decision,
                            "selected_metric_id": item.selected_metric_id,
                            "confidence": item.confidence,
                            "reason_code": item.reason_code,
                        }
                        for item in payload.decisions
                    ],
                },
            },
            "adjudication_token": "",
        }
    )
