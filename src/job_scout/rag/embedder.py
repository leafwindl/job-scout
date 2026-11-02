"""本地向量化：用 fastembed 跑 bge-small-zh，不依赖任何 API。

为什么本地：
- 不花钱、不限流，评测可以反复跑
- 向量维度 512，模型约 95MB，CPU 上 453 条几秒钟
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
CACHE_DIR = Path("index/cache")


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name, cache_dir=str(CACHE_DIR))

    def encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """返回 L2 归一化后的向量矩阵，行向量点积即余弦相似度。"""
        if not texts:
            return np.zeros((0, 512), dtype=np.float32)
        vectors = list(self._model.embed(texts, batch_size=batch_size))
        arr = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.clip(norms, 1e-8, None)
