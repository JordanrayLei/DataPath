from __future__ import annotations

import re

from rank_bm25 import BM25Okapi


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[a-z0-9_]+", re.IGNORECASE)


def tokenize_search_text(text: str) -> list[str]:
    tokens: list[str] = []
    for part in TOKEN_PATTERN.findall(text.casefold()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part)
            tokens.extend(part[index : index + 2] for index in range(len(part) - 1))
        else:
            tokens.append(part)
    return tokens


def bm25_relevance_scores(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    tokenized_documents = [tokenize_search_text(document) for document in documents]
    query_tokens = tokenize_search_text(query)
    if not query_tokens or not any(tokenized_documents):
        return [0.0] * len(documents)
    raw_scores = BM25Okapi(tokenized_documents).get_scores(query_tokens)
    positive_max = max((float(score) for score in raw_scores if score > 0), default=0.0)
    if positive_max <= 0:
        return [0.0] * len(documents)
    return [max(0.0, float(score)) / positive_max for score in raw_scores]
