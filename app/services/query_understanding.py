from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Metric
from app.config import get_settings


@dataclass(frozen=True)
class QueryUnderstanding:
    normalized_query: str
    metric_mentions: list[str]
    provider: str
    inherited_metric: bool
    dimension_mentions: list[str] | None = None
    filter_mentions: list[dict] | None = None
    time_text: str = ""
    time_start: str | None = None
    time_end: str | None = None


class QueryUnderstandingProvider(Protocol):
    def understand(
        self,
        session: Session,
        query: str,
        domain: str,
        inherited_metric_name: str = "",
    ) -> QueryUnderstanding: ...


class MetricCenterUnderstandingProvider:
    """Deterministic provider backed by published metric semantic assets."""

    name = "metric_center_hybrid"

    def understand(
        self,
        session: Session,
        query: str,
        domain: str,
        inherited_metric_name: str = "",
    ) -> QueryUnderstanding:
        normalized = query.strip()
        lowered = normalized.casefold()
        metrics = session.scalars(
            select(Metric)
            .options(selectinload(Metric.aliases), selectinload(Metric.semantic_profile))
            .where(
                Metric.business_domain_id == domain,
                Metric.status == "PUBLISHED",
            )
        ).all()

        has_signal = False
        for metric in metrics:
            terms = [metric.name, *(alias.alias for alias in metric.aliases)]
            if any(term.casefold() in lowered for term in terms if term):
                has_signal = True
                break
            profile = metric.semantic_profile
            examples = profile.positive_examples_json if profile else []
            if any(
                SequenceMatcher(None, lowered, str(example).casefold()).ratio() >= 0.62
                for example in examples
            ):
                has_signal = True
                break

        if has_signal:
            mentions = [normalized]
            inherited = False
        elif inherited_metric_name:
            mentions = [inherited_metric_name]
            inherited = True
        else:
            mentions = [normalized]
            inherited = False

        return QueryUnderstanding(
            normalized_query=normalized,
            metric_mentions=mentions,
            provider=self.name,
            inherited_metric=inherited,
        )


class HttpQueryUnderstandingProvider:
    """Adapter for an LLM/Dify endpoint that returns constrained JSON only."""

    name = "http_structured_llm"

    def __init__(self, fallback: QueryUnderstandingProvider) -> None:
        self.fallback = fallback

    def understand(
        self,
        session: Session,
        query: str,
        domain: str,
        inherited_metric_name: str = "",
    ) -> QueryUnderstanding:
        settings = get_settings()
        if not settings.query_understanding_url:
            return self.fallback.understand(session, query, domain, inherited_metric_name)
        headers = {"Content-Type": "application/json"}
        if settings.query_understanding_token:
            headers["Authorization"] = f"Bearer {settings.query_understanding_token}"
        try:
            with httpx.Client(
                timeout=settings.query_understanding_timeout_seconds,
                trust_env=False,
            ) as client:
                response = client.post(
                    settings.query_understanding_url,
                    headers=headers,
                    json={
                        "query": query,
                        "business_domain": domain,
                        "inherited_metric_name": inherited_metric_name,
                        "response_schema": {
                            "normalized_query": "string",
                            "metric_mentions": ["string"],
                            "dimension_mentions": ["string"],
                            "filter_mentions": [{"dimension": "string", "operator": "string", "values": ["string"]}],
                            "time_text": "string",
                            "time_start": "YYYY-MM-DD|null",
                            "time_end": "YYYY-MM-DD|null",
                        },
                    },
                )
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data", payload)
                mentions = data.get("metric_mentions")
                if not isinstance(mentions, list):
                    raise ValueError("metric_mentions must be a list")
                return QueryUnderstanding(
                    normalized_query=str(data.get("normalized_query") or query).strip(),
                    metric_mentions=[str(item).strip() for item in mentions if str(item).strip()],
                    provider=self.name,
                    inherited_metric=bool(data.get("inherited_metric", False)),
                    dimension_mentions=[str(item) for item in (data.get("dimension_mentions") or [])],
                    filter_mentions=[item for item in (data.get("filter_mentions") or []) if isinstance(item, dict)],
                    time_text=str(data.get("time_text") or ""),
                    time_start=str(data["time_start"]) if data.get("time_start") else None,
                    time_end=str(data["time_end"]) if data.get("time_end") else None,
                )
        except (httpx.HTTPError, ValueError, TypeError):
            return self.fallback.understand(session, query, domain, inherited_metric_name)


def get_query_understanding_provider() -> QueryUnderstandingProvider:
    fallback = MetricCenterUnderstandingProvider()
    if get_settings().query_understanding_provider == "http":
        return HttpQueryUnderstandingProvider(fallback)
    return fallback
