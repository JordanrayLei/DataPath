from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

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


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> EmbeddingBatch: ...


def _local_features(text: str) -> list[tuple[str, float]]:
    normalized = re.sub(r"\s+", "", text.casefold())
    features: list[tuple[str, float]] = []
    for size, weight in ((1, 0.5), (2, 1.0), (3, 1.25)):
        features.extend(
            (f"c{size}:{normalized[index:index + size]}", weight)
            for index in range(max(0, len(normalized) - size + 1))
        )
    words = re.findall(r"[a-z0-9_]+", text.casefold())
    features.extend((f"w:{word}", 1.5) for word in words)
    return features


class LocalCharNgramEmbeddingProvider:
    """Deterministic offline retrieval vectors; no text leaves the process."""

    model = "local-char-ngram-v1"

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        settings = get_settings()
        if not texts:
            return EmbeddingBatch([], self.model, settings.embedding_dimensions, 0)
        if len(texts) > settings.embedding_batch_size:
            raise EmbeddingProviderError("embedding batch exceeds configured batch size")
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * settings.embedding_dimensions
            for feature, weight in _local_features(text):
                digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
                index = int.from_bytes(digest[:8], "big") % settings.embedding_dimensions
                sign = 1.0 if digest[8] & 1 else -1.0
                vector[index] += sign * weight
            norm = math.sqrt(sum(value * value for value in vector))
            vectors.append([value / norm for value in vector] if norm else vector)
        return EmbeddingBatch(
            vectors=vectors,
            model=self.model,
            dimensions=settings.embedding_dimensions,
            total_tokens=sum(len(text) for text in texts),
        )


@lru_cache(maxsize=2)
def _load_sentence_transformer(model_name: str, device: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise EmbeddingProviderError(
            "sentence-transformers is required for local_sentence_transformer"
        ) from error
    try:
        return SentenceTransformer(model_name, device=device)
    except Exception as error:
        raise EmbeddingProviderError(f"local embedding model could not be loaded: {error}") from error


class LocalSentenceTransformerEmbeddingProvider:
    """Run a downloaded Sentence Transformers model without exporting input text."""

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        settings = get_settings()
        if not texts:
            return EmbeddingBatch([], settings.embedding_model, settings.embedding_dimensions, 0)
        if len(texts) > settings.embedding_batch_size:
            raise EmbeddingProviderError("embedding batch exceeds configured batch size")
        model = _load_sentence_transformer(
            settings.local_sentence_transformer_model,
            settings.local_sentence_transformer_device,
        )
        try:
            encoded = model.encode(
                texts,
                batch_size=settings.embedding_batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as error:
            raise EmbeddingProviderError(f"local embedding request failed: {error}") from error
        vectors: list[list[float]] = []
        for row in encoded:
            vector = [float(value) for value in row.tolist()]
            if len(vector) > settings.embedding_dimensions:
                raise EmbeddingProviderError(
                    "local embedding dimensions exceed the configured pgvector width"
                )
            vectors.append(vector + [0.0] * (settings.embedding_dimensions - len(vector)))
        return EmbeddingBatch(
            vectors=vectors,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            total_tokens=sum(len(text) for text in texts),
        )


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


def get_embedding_provider() -> EmbeddingProvider:
    provider = get_settings().embedding_provider.strip().casefold()
    if provider == "dashscope":
        return DashScopeEmbeddingProvider()
    if provider == "local_char_ngram":
        return LocalCharNgramEmbeddingProvider()
    if provider == "local_sentence_transformer":
        return LocalSentenceTransformerEmbeddingProvider()
    raise EmbeddingProviderError(f"unsupported embedding provider: {provider}")
