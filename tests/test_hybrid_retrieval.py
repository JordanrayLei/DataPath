from app.services.bm25_retrieval import bm25_relevance_scores, tokenize_search_text


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
