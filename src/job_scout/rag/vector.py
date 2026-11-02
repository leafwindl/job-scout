"""向量索引：整库暴力检索。

为什么不面向量库：
453 条 × 512 维，一次矩阵乘法 < 5ms。引入 Chroma/Milvus 只增加运维成本。
数据涨到 10 万条再换。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from job_scout.rag.corpus import Doc
from job_scout.rag.embedder import Embedder

INDEX_DIR = Path("index")


class VectorRetriever:
    name = "vector"

    def __init__(self, docs: list[Doc], vectors: np.ndarray, embedder: Embedder) -> None:
        self.docs = docs
        self.vectors = vectors
        self.embedder = embedder

    @classmethod
    def build(
        cls,
        docs: list[Doc],
        embedder: Embedder,
        index_dir: Path = INDEX_DIR,
        force: bool = False,
    ) -> VectorRetriever:
        index_dir.mkdir(parents=True, exist_ok=True)
        vec_path = index_dir / "vectors.npy"
        meta_path = index_dir / "vectors_meta.json"

        if not force and vec_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            cached_ids = meta.get("doc_ids", [])
            if cached_ids == [d.doc_id for d in docs] and meta.get("model") == embedder.model_name:
                vectors = np.load(vec_path)
                return cls(docs, vectors, embedder)

        vectors = embedder.encode([d.text for d in docs])
        np.save(vec_path, vectors)
        meta_path.write_text(
            json.dumps(
                {"doc_ids": [d.doc_id for d in docs], "model": embedder.model_name},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return cls(docs, vectors, embedder)

    def search(self, query: str, k: int = 10) -> list[tuple[Doc, float]]:
        q = self.embedder.encode([query])[0]
        scores = self.vectors @ q
        order = np.argsort(scores)[::-1][:k]
        return [(self.docs[i], float(scores[i])) for i in order]

    def score(self, query: str) -> np.ndarray:
        """全库打分，融合时用。"""
        q = self.embedder.encode([query])[0]
        return self.vectors @ q
