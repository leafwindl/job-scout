"""BM25 检索基线。

为什么先做 BM25：
1. 不依赖任何 API / GPU，能立刻跑出数字
2. 中文岗位检索里「LangGraph」「RAG」这类专有名词，BM25 往往比向量更准
3. 有了基线，后面加向量检索才有对比对象——「提升多少」比「用了向量」值钱
"""

from __future__ import annotations

import re

import jieba
import numpy as np
from rank_bm25 import BM25Okapi

from job_scout.rag.corpus import Doc

# 中文停用词（精简版，够用）
STOPWORDS = set(
    "的 了 和 与 及 或 在 是 有 能 会 对 为 等 中 上 下 个 我 你 他 她 它 这 那 "
    "我们 你们 他们 一个 一些 可以 进行 负责 参与 以及 相关 工作 岗位 要求 优先".split()
)

# 英文/数字 token 或连续中文，分开处理
TOKEN_RE = re.compile(r"[a-z0-9_+#./-]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """中英混合分词。

    英文技术词整体保留（langgraph / c++ / k8s），
    中文交给 jieba，再过滤单字和停用词。
    """
    text = (text or "").lower()
    out: list[str] = []
    for m in TOKEN_RE.finditer(text):
        seg = m.group()
        if seg[0].isascii():
            if len(seg) >= 2:
                out.append(seg)
        else:
            for w in jieba.lcut(seg):
                w = w.strip()
                if len(w) >= 2 and w not in STOPWORDS:
                    out.append(w)
    return out


class BM25Retriever:
    name = "bm25"

    def __init__(self, docs: list[Doc], field: str = "text") -> None:
        """field: "text" 用增强字段建索引，"text_raw" 只用标题+正文（对照实验）。"""
        self.docs = docs
        self.field = field
        self._tokens = [tokenize(getattr(d, field)) for d in docs]
        self._bm25 = BM25Okapi(self._tokens)

    def search(self, query: str, k: int = 10) -> list[tuple[Doc, float]]:
        q = tokenize(query)
        if not q:
            return []
        scores = self._bm25.get_scores(q)
        order = np.argsort(scores)[::-1][:k]
        return [(self.docs[i], float(scores[i])) for i in order if scores[i] > 0]
