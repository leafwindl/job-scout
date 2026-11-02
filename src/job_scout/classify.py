"""JD 方向分类：按技术关键词把岗位归到某条技术线上。

分类是启发式的（关键词打分），不是语义模型：
- 权重高的是「决定性信号」（如 LangGraph、RAG、微调、全栈）
- 最高分不到阈值就归到「通用/后端底子」
"""

from __future__ import annotations

import re

CATEGORIES: dict[str, list[tuple[str, int]]] = {
    "RAG/知识库": [
        (r"\brag\b|检索增强", 4),
        (r"知识库", 3),
        (r"向量|embedding|faiss|milvus|chroma|qdrant", 2),
        (r"召回|检索", 1),
    ],
    "Agent 编排": [
        (r"langgraph|langchain|autogen|crewai|llamaindex", 3),
        (r"multi[- ]?agent|多智能体|多\s*agent", 4),
        (r"function\s*calling|tool\s*calling|工具调用", 3),
        (r"\bmcp\b", 3),
        (r"工作流|编排|orchestrat", 2),
    ],
    "算法/模型": [
        (r"微调|fine[- ]?tun|lora|\bsft\b|rlhf", 4),
        (r"pytorch|tensorflow|deepspeed", 2),
        (r"训练|模型压缩|蒸馏|量化", 2),
        (r"论文|顶会|sci|ei\b", 1),
    ],
    "全栈/前端": [
        (r"typescript|javascript|\breact\b|\bvue\b|前端", 3),
        (r"全栈", 4),
        (r"小程序|\bapp\b|移动端", 2),
    ],
    "数据工程": [
        (r"爬虫|scrapy", 4),
        (r"数据清洗|\betl\b|数据管道", 3),
        (r"spark|hadoop|flink", 2),
    ],
    "后端/平台": [
        (r"python", 1),
        (r"java|golang|\bgo\b", 1),
        (r"mysql|postgres|redis|mongodb", 1),
        (r"微服务|分布式|docker|k8s|kubernetes", 1),
        (r"fastapi|flask|django|spring", 1),
        (r"后端|服务端|平台", 1),
    ],
}

THRESHOLD = 4
FALLBACK = "通用/后端底子"


def classify(text: str) -> tuple[str, dict[str, int]]:
    low = (text or "").lower()
    scores: dict[str, int] = {}
    for cat, rules in CATEGORIES.items():
        s = 0
        for pat, w in rules:
            if re.search(pat, low):
                s += w
        scores[cat] = s

    best = max(scores, key=scores.get)
    if scores[best] < THRESHOLD:
        return FALLBACK, scores
    return best, scores
