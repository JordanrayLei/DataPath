from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import get_settings


class EmbeddingProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    model: str
    dimensions: int
    total_tokens: int


class DashScopeEmbeddingProvider:
    def embed(self, texts: list[str]) -> EmbeddingBatch:
        settings = get_settings()
        if not settings.dashscope_api_key:
            raise EmbeddingProviderError("DASHSCOPE_API_KEY is not configured")
        if not texts:
            return EmbeddingBatch([], settings.embedding_model, settings.embedding_dimensions, 0)
        if len(texts) > settings.embedding_batch_size:
            raise EmbeddingProviderError("embedding batch exceeds configured batch size")

        endpoint = f"{settings.embedding_base_url.rstrip('/')}/embeddings"
        try:
            with httpx.Client(timeout=settings.embedding_timeout_seconds, trust_env=False) as client:
                response = client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {settings.dashscope_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.embedding_model,
                        "input": texts,
                        "dimensions": settings.embedding_dimensions,
                        "encoding_format": "float",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise EmbeddingProviderError(f"DashScope embedding request failed: {error}") from error

        rows = sorted(payload.get("data") or [], key=lambda item: int(item.get("index", 0)))
        vectors = [item.get("embedding") for item in rows]
        if len(vectors) != len(texts) or any(not isinstance(item, list) for item in vectors):
            raise EmbeddingProviderError("DashScope embedding response is incomplete")
        if any(len(item) != settings.embedding_dimensions for item in vectors):
            raise EmbeddingProviderError("DashScope embedding dimensions do not match configuration")
        return EmbeddingBatch(
            vectors=vectors,
            model=str(payload.get("model") or settings.embedding_model),
            dimensions=settings.embedding_dimensions,
            total_tokens=int((payload.get("usage") or {}).get("total_tokens") or 0),
        )


def get_embedding_provider() -> DashScopeEmbeddingProvider:
    return DashScopeEmbeddingProvider()
