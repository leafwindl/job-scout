"""LLM 重排器（cross-encoder 的替代方案）。

为什么用它：
本机 HuggingFace 大文件下载被限流（tokenizer 能下，model.onnx 0 字节），
`bge-reranker-base` 拉不动。LLM 重排不需要下载，且对中文理解更好。

代价：
- 慢：一次 listwise 调用约 2-4 秒
- 花钱：每次约 5000 token

所以只在「候选少 + 分差小」时触发——这正好是自适应路由的设计初衷。
"""

from __future__ import annotations

import re

from job_scout.rag.corpus import Doc

SYS = """你是招聘岗位的相关性评审。给定一个查询和若干候选岗位，按与查询的相关程度排序。

规则：
1. 只输出编号，从最相关到最不相关，用英文逗号分隔，例如：3,1,5,2,4
2. 不要输出任何解释、标点或多余文字
3. 必须包含所有候选编号，每个只出现一次
"""


class LLMReranker:
    def __init__(self, llm, max_doc_chars: int = 110) -> None:
        self.llm = llm
        self.max_doc_chars = max_doc_chars
        self.errors = 0
        self.last_error = ""

    def _build_prompt(self, query: str, docs: list[Doc]) -> str:
        lines: list[str] = []
        for i, d in enumerate(docs, start=1):
            body = " ".join(d.text.split("\n", 1)[-1].split())[: self.max_doc_chars]
            lines.append(f"[{i}] {d.title}｜{d.company}\n{body}")
        return f"查询：{query}\n\n候选岗位：\n" + "\n\n".join(lines) + "\n\n排序结果："

    def _parse(self, raw: str, n: int) -> list[int] | None:
        nums = [int(x) for x in re.findall(r"\d+", raw)]
        order: list[int] = []
        seen: set[int] = set()
        for x in nums:
            if 1 <= x <= n and x not in seen:
                seen.add(x)
                order.append(x)
        # 只要认出四分之一就算成功：模型经常只返回前几名，
        # 之前要求一半，导致大半调用都白跑（实测失败率 76%）
        if len(order) < max(2, n // 4):
            return None
        # 补上缺失的编号，保持稳定
        order += [i for i in range(1, n + 1) if i not in seen]
        return order

    def score(self, query: str, docs: list[Doc]) -> list[float]:
        """返回与 docs 对齐的分数，越靠前越高。"""
        n = len(docs)
        if n == 0:
            return []
        try:
            raw = self.llm.complete(SYS, self._build_prompt(query, docs), temperature=0.0)
            order = self._parse(raw, n)
            if order is None:
                raise ValueError(f"排序结果不完整: {raw[:60]}")
        except Exception as e:  # noqa: BLE001
            self.errors += 1
            self.last_error = f"{type(e).__name__}: {str(e)[:200]}"
            # 失败就保持原顺序（相当于不重排），不能让整条查询崩掉
            return [float(n - i) for i in range(n)]

        scores = [0.0] * n
        for rank, idx in enumerate(order, start=1):
            scores[idx - 1] = 1.0 / rank
        return scores
