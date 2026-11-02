"""混合检索：RRF 融合 + 自适应重排。

两个关键设计：

1. **RRF 而不是加权求和**
   BM25 分数（无量纲，随查询长度变化）和余弦相似度（0~1）量纲不同，
   直接加权需要反复调参且不稳定。RRF 只取排名：score = Σ 1/(k + rank)，
   天然可比，无需归一化。

2. **自适应重排**
   融合后 Top1 与 Top2 分差足够大时，重排不可能改变顺序——
   直接跳过，省一次模型调用。分差小才真去重排。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from job_scout.rag.corpus import Doc


class Retriever(Protocol):
    name: str

    def search(self, query: str, k: int = 10) -> list[tuple[Doc, float]]: ...


def rrf_fuse(
    results_list: list[list[tuple[Doc, float]]],
    k: int = 60,
) -> list[tuple[Doc, float]]:
    """Reciprocal Rank Fusion。k 是平滑常数，论文常用 60。"""
    scores: dict[str, float] = defaultdict(float)
    doc_map: dict[str, Doc] = {}

    for results in results_list:
        for rank, (doc, _) in enumerate(results, start=1):
            doc_map[doc.doc_id] = doc
            scores[doc.doc_id] += 1.0 / (k + rank)

    ordered = sorted(scores.items(), key=lambda x: -x[1])
    return [(doc_map[doc_id], s) for doc_id, s in ordered]


class HybridRetriever:
    name = "hybrid"

    def __init__(self, bm25: Retriever, vector: Retriever, pool: int = 50) -> None:
        self.bm25 = bm25
        self.vector = vector
        self.pool = pool

    def search(self, query: str, k: int = 10) -> list[tuple[Doc, float]]:
        bm = self.bm25.search(query, k=self.pool)
        vs = self.vector.search(query, k=self.pool)
        return rrf_fuse([bm, vs])[:k]


class Reranker(Protocol):
    def score(self, query: str, docs: list[Doc]) -> list[float]: ...


class AdaptiveRerankRetriever:
    """先融合，再按分差决定要不要重排。"""

    name = "hybrid+adaptive-rerank"

    def __init__(
        self,
        base: Retriever,
        reranker: Reranker | None = None,
        pool: int = 20,
        gap_threshold: float = 0.05,
    ) -> None:
        self.base = base
        self.reranker = reranker
        self.pool = pool
        self.gap_threshold = gap_threshold
        self.stats = {"reranked": 0, "skipped": 0, "no_reranker": 0}
        self.gaps: list[float] = []

    def _gap(self, candidates: list[tuple[Doc, float]]) -> float:
        """相对分差：(top1 - top2) / top1。"""
        if len(candidates) < 2:
            return 1.0
        top = candidates[0][1]
        if top <= 0:
            return 0.0
        return (top - candidates[1][1]) / top

    def search(self, query: str, k: int = 10) -> list[tuple[Doc, float]]:
        candidates = self.base.search(query, k=self.pool)
        gap = self._gap(candidates)
        self.gaps.append(gap)

        # 没有 reranker：不能算「跳过」，只是没这能力，单独计数
        if self.reranker is None:
            self.stats["no_reranker"] += 1
            return candidates[:k]

        # 分差够大 → 重排不可能改变顺序，跳过
        if gap > self.gap_threshold:
            self.stats["skipped"] += 1
            return candidates[:k]

        self.stats["reranked"] += 1
        docs = [d for d, _ in candidates]
        scores = self.reranker.score(query, docs)
        reranked = sorted(zip(docs, scores, strict=False), key=lambda x: -x[1])
        return reranked[:k]
