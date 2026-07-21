from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import replace
from typing import Iterable

from it_ops_agent.schema import Chunk, RetrievedChunk


def tokenize(text: str) -> list[str]:
    lower = text.lower()
    tokens = re.findall(r"[a-zA-Z0-9_\-]+", lower)
    domain_terms = [
        "密码",
        "重置",
        "账号",
        "解锁",
        "服务",
        "重启",
        "工单",
        "查询",
        "认证",
        "失败",
        "人工确认",
        "高风险",
        "健康检查",
    ]
    tokens.extend(term for term in domain_terms if term in lower)
    for segment in re.findall(r"[\u4e00-\u9fff]+", lower):
        tokens.extend(segment)
        tokens.extend(segment[idx : idx + 1] for idx in range(len(segment)))
        tokens.extend(segment[idx : idx + 2] for idx in range(max(0, len(segment) - 1)))
        tokens.extend(segment[idx : idx + 3] for idx in range(max(0, len(segment) - 2)))
    return tokens


class BM25Retriever:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(chunk.content) for chunk in chunks]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lengths) / max(1, len(self.doc_lengths))
        self.df = Counter()
        for tokens in self.doc_tokens:
            self.df.update(set(tokens))

    def search(self, query: str) -> dict[str, float]:
        scores: dict[str, float] = {}
        query_terms = tokenize(query)
        total_docs = len(self.chunks)
        for chunk, tokens, doc_len in zip(self.chunks, self.doc_tokens, self.doc_lengths):
            tf = Counter(tokens)
            score = 0.0
            for term in query_terms:
                if term not in tf:
                    continue
                idf = math.log(1 + (total_docs - self.df[term] + 0.5) / (self.df[term] + 0.5))
                numerator = tf[term] * (self.k1 + 1)
                denominator = tf[term] + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += idf * numerator / denominator
            scores[chunk.chunk_id] = score
        return scores


class HashingVectorRetriever:
    def __init__(self, chunks: list[Chunk], dimensions: int = 384) -> None:
        self.chunks = chunks
        self.dimensions = dimensions
        self.vectors = {chunk.chunk_id: self.embed(chunk.content) for chunk in chunks}

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % self.dimensions
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[idx] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def search(self, query: str) -> dict[str, float]:
        query_vector = self.embed(query)
        return {
            chunk.chunk_id: cosine(query_vector, self.vectors[chunk.chunk_id])
            for chunk in self.chunks
        }


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], bm25_weight: float = 0.55) -> None:
        self.chunks = chunks
        self.bm25 = BM25Retriever(chunks)
        self.vector = HashingVectorRetriever(chunks)
        self.bm25_weight = bm25_weight

    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        bm25_scores = normalize_scores(self.bm25.search(query))
        vector_scores = normalize_scores(self.vector.search(query))
        results: list[RetrievedChunk] = []
        for chunk in self.chunks:
            bm25_score = bm25_scores.get(chunk.chunk_id, 0.0)
            vector_score = vector_scores.get(chunk.chunk_id, 0.0)
            hybrid = self.bm25_weight * bm25_score + (1 - self.bm25_weight) * vector_score
            results.append(
                RetrievedChunk(
                    chunk=chunk,
                    bm25_score=bm25_score,
                    vector_score=vector_score,
                    hybrid_score=hybrid,
                )
            )
        return sorted(results, key=lambda item: item.hybrid_score, reverse=True)[:top_k]


class LightweightReranker:
    def rerank(self, query: str, candidates: Iterable[RetrievedChunk]) -> list[RetrievedChunk]:
        query_terms = set(tokenize(query))
        reranked: list[RetrievedChunk] = []
        for item in candidates:
            content_terms = set(tokenize(item.chunk.content))
            overlap = len(query_terms & content_terms) / max(1, len(query_terms))
            title_bonus = 0.08 if any(term in item.chunk.title.lower() for term in query_terms) else 0.0
            score = 0.70 * item.hybrid_score + 0.30 * overlap + title_bonus
            reranked.append(replace(item, rerank_score=score))
        return sorted(reranked, key=lambda item: item.rerank_score, reverse=True)


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    values = list(scores.values())
    min_score = min(values)
    max_score = max(values)
    if math.isclose(min_score, max_score):
        return {key: 0.0 for key in scores}
    return {key: (value - min_score) / (max_score - min_score) for key, value in scores.items()}


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
