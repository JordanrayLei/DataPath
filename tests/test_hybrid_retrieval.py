import math
from types import SimpleNamespace

from app.config import get_settings
from app.services.bm25_retrieval import bm25_relevance_scores, tokenize_search_text
from app.services.embedding_provider import (
    LocalCharNgramEmbeddingProvider,
    LocalSentenceTransformerEmbeddingProvider,
)
from app.services.metric_retrieval import (
    rerank_scored_candidates,
    retrieval_runtime_diagnostics,
)
from app.services.metric_vector_index import normalize_vector_query


def test_chinese_tokenizer_emits_unigrams_and_bigrams() -> None:
    tokens = tokenize_search_text("查询销售额 trend_2026")
    assert "销" in tokens
    assert "销售" in tokens
    assert "销售额" not in tokens
    assert "trend_2026" in tokens


def test_bm25_ranks_matching_metric_document_first() -> None:
    documents = [
        "指标名称：真实净收入。销售额扣除取消金额后的净收入。",
        "指标名称：真实订单量。非取消发票的去重订单数。",
        "指标名称：真实买家数。去重购买客户数。",
    ]
    scores = bm25_relevance_scores("扣掉撤销交易后的收入", documents)
    assert scores[0] == max(scores)
    assert scores[0] > scores[1]


def test_retrieval_runtime_diagnostics_exposes_safe_fallback_state() -> None:
    diagnostics = retrieval_runtime_diagnostics()

    assert diagnostics["embedding_provider"]
    assert isinstance(diagnostics["embedding_configured"], bool)
    assert diagnostics["lexical_fallback"] == "BM25_CANDIDATES_REQUIRE_CLARIFICATION"


def test_local_sentence_transformer_is_configured_without_external_key(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local_sentence_transformer")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "")
    get_settings.cache_clear()
    try:
        diagnostics = retrieval_runtime_diagnostics()
    finally:
        get_settings.cache_clear()

    assert diagnostics["embedding_configured"] is True
    assert diagnostics["reranker_configured"] is False


def test_vector_query_removes_time_and_presentation_text() -> None:
    assert normalize_vector_query("请查看2024年顾客实际付了多少") == "顾客实际付了多少"


def test_empty_reranker_result_does_not_change_candidates(monkeypatch) -> None:
    class EmptyReranker:
        def rerank(self, query, documents):
            return []

    first = SimpleNamespace(metric=SimpleNamespace(id="M_A"))
    second = SimpleNamespace(metric=SimpleNamespace(id="M_B"))
    scored = [(0.8, ["embedding"], first), (0.7, ["bm25"], second)]
    monkeypatch.setattr(
        "app.services.metric_retrieval.get_reranker_provider",
        lambda: EmptyReranker(),
    )
    monkeypatch.setattr(
        "app.services.metric_retrieval.metric_search_document",
        lambda record: record.metric.id,
    )

    assert rerank_scored_candidates("query", scored) == scored


def test_local_char_ngram_embedding_is_deterministic_and_normalized(monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local_char_ngram")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "64")
    get_settings.cache_clear()
    try:
        batch = LocalCharNgramEmbeddingProvider().embed(["实际回款到账", "实际回款到账"])
    finally:
        get_settings.cache_clear()

    assert batch.model == "local-char-ngram-v1"
    assert batch.vectors[0] == batch.vectors[1]
    assert len(batch.vectors[0]) == 64
    assert math.isclose(sum(value * value for value in batch.vectors[0]), 1.0)


def test_local_sentence_transformer_pads_to_pgvector_width(monkeypatch) -> None:
    class FakeArray:
        def __init__(self, values):
            self.values = values

        def tolist(self):
            return self.values

    class FakeModel:
        def encode(self, texts, **kwargs):
            assert texts == ["实际到账"]
            assert kwargs["normalize_embeddings"] is True
            return [FakeArray([0.6, 0.8])]

    monkeypatch.setenv("EMBEDDING_PROVIDER", "local_sentence_transformer")
    monkeypatch.setenv("EMBEDDING_MODEL", "test-local-model")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "4")
    monkeypatch.setattr(
        "app.services.embedding_provider._load_sentence_transformer",
        lambda model_name, device: FakeModel(),
    )
    get_settings.cache_clear()
    try:
        batch = LocalSentenceTransformerEmbeddingProvider().embed(["实际到账"])
    finally:
        get_settings.cache_clear()

    assert batch.model == "test-local-model"
    assert batch.vectors == [[0.6, 0.8, 0.0, 0.0]]
