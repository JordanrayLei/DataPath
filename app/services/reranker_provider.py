from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import get_settings


class RerankerProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class RerankScore:
    index: int
    relevance_score: float


class DashScopeRerankerProvider:
    def rerank(self, query: str, documents: list[str]) -> list[RerankScore]:
        settings = get_settings()
        if not settings.reranker_enabled or not documents:
            return []
        if not settings.dashscope_api_key:
            raise RerankerProviderError("DASHSCOPE_API_KEY is not configured")

        try:
            with httpx.Client(timeout=settings.reranker_timeout_seconds, trust_env=False) as client:
                response = client.post(
                    f"{settings.reranker_base_url.rstrip('/')}/reranks",
                    headers={
                        "Authorization": f"Bearer {settings.dashscope_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.reranker_model,
                        "query": query,
                        "documents": documents,
                        "top_n": len(documents),
                        "instruct": "Retrieve the metric definition that best matches the user's analytics intent.",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RerankerProviderError(f"DashScope rerank request failed: {error}") from error

        results: list[RerankScore] = []
        for item in payload.get("results") or []:
            index = int(item.get("index", -1))
            score = float(item.get("relevance_score", 0.0))
            if 0 <= index < len(documents):
                results.append(RerankScore(index=index, relevance_score=max(0.0, min(1.0, score))))
        if len(results) != len(documents):
            raise RerankerProviderError("DashScope rerank response is incomplete")
        return results


def get_reranker_provider() -> DashScopeRerankerProvider:
    return DashScopeRerankerProvider()
