"""RAG 统一入口：把语料、检索、生成组装成一个对象。

CLI 和 API 共用，避免两边各写一遍初始化逻辑。
模型加载较重，用模块级单例缓存。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from job_scout.rag.bm25 import BM25Retriever
from job_scout.rag.corpus import load_docs
from job_scout.rag.generate import Answer
from job_scout.rag.generate import ask as ask_impl
from job_scout.rag.hybrid import AdaptiveRerankRetriever, HybridRetriever
from job_scout.rag.llm import get_llm


@dataclass
class RagPipeline:
    docs: list
    retriever: AdaptiveRerankRetriever
    llm: object | None

    @property
    def has_llm(self) -> bool:
        return self.llm is not None

    def search(self, query: str, k: int = 10):
        return self.retriever.search(query, k=k)

    def ask(
        self,
        question: str,
        k: int = 5,
        max_chars: int = 4000,
        profile_text: str = "",
    ) -> Answer:
        return ask_impl(
            question,
            self.retriever,
            llm=self.llm,
            k=k,
            max_chars=max_chars,
            profile_text=profile_text,
        )


@lru_cache(maxsize=2)
def get_pipeline(db_path: str = "data/job_scout.db", only_intern: bool = True) -> RagPipeline:
    docs = load_docs(db_path, only_intern=only_intern)
    if not docs:
        raise RuntimeError("没有可用文档，先采集并抓取 JD")

    bm25 = BM25Retriever(docs, field="text")

    # 向量检索依赖 fastembed；容器里为减小体积没装，降级为纯 BM25
    try:
        from job_scout.rag.embedder import Embedder
        from job_scout.rag.vector import VectorRetriever

        embedder = Embedder()
        vector = VectorRetriever.build(docs, embedder, index_dir=Path("index"))
        hybrid = HybridRetriever(bm25, vector)
        retriever = AdaptiveRerankRetriever(hybrid)
    except Exception as e:  # noqa: BLE001
        print(f"[rag] 向量检索不可用（{type(e).__name__}），降级为 BM25", flush=True)
        retriever = AdaptiveRerankRetriever(bm25)

    return RagPipeline(docs=docs, retriever=retriever, llm=get_llm())


def reset_pipeline() -> None:
    get_pipeline.cache_clear()
