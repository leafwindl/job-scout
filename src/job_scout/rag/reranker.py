"""Cross-encoder 重排器。

为什么需要重排：
BM25 / 向量都是「双塔」式的粗召回——query 和文档分开编码，没有交互。
Cross-encoder 把 (query, 文档) 拼在一起打分，精度高但慢，所以只对 Top-N 做。

为什么只对 Top-20 做：
单条重排约 30-80ms，20 条就 1 秒以上。全库重排不可行。
"""

from __future__ import annotations

from pathlib import Path

from job_scout.rag.corpus import Doc

MODEL_NAME = "BAAI/bge-reranker-base"
CACHE_DIR = Path("index/cache")
MAX_DOC_CHARS = 900


def model_available(min_mb: int = 200) -> bool:
    """检查重排模型是否已下载完整。

    HuggingFace 大文件在本机被限流时只会留下 tokenizer，
    直接构造 TextCrossEncoder 会卡在下载上，所以先探测。
    """
    if not CACHE_DIR.exists():
        return False
    for p in CACHE_DIR.rglob("*.onnx"):
        if "reranker" in str(p).lower() and p.stat().st_size > min_mb * 1024 * 1024:
            return True
    return False


class CrossEncoderReranker:
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self.model_name = model_name
        self._model = TextCrossEncoder(model_name=model_name, cache_dir=str(CACHE_DIR))

    def score(self, query: str, docs: list[Doc]) -> list[float]:
        if not docs:
            return []
        # 截断：JD 太长会拖慢重排，前 900 字足够判断相关性
        texts = [d.text[:MAX_DOC_CHARS] for d in docs]
        return [float(s) for s in self._model.rerank(query, texts)]
