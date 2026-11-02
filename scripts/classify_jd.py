"""把实习 JD 按技术方向分类，输出每个方向的数量、要求和代表岗位。"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter

# 每个方向的关键词及权重。权重高的是「决定性信号」。
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

THRESHOLD = 4  # 最高分不到 4 就归到「通用/后端底子」


def classify(text: str) -> tuple[str, dict[str, int]]:
    low = text.lower()
    scores: dict[str, int] = {}
    for cat, rules in CATEGORIES.items():
        s = 0
        for pat, w in rules:
            if re.search(pat, low):
                s += w
        scores[cat] = s

    best = max(scores, key=scores.get)
    if scores[best] < THRESHOLD:
        return "通用/后端底子", scores
    return best, scores


def main() -> None:
    conn = sqlite3.connect("data/job_scout.db")
    rows = conn.execute(
        "SELECT title, company, salary_raw, district, description, url FROM postings "
        "WHERE title LIKE '%实习%' AND description IS NOT NULL AND description != ''"
    ).fetchall()

    groups: dict[str, list[dict]] = {}
    for title, company, salary, district, desc, url in rows:
        cat, scores = classify(desc)
        groups.setdefault(cat, []).append(
            {
                "title": title,
                "company": company,
                "salary": salary,
                "district": district,
                "desc": desc,
                "url": url,
                "scores": scores,
            }
        )

    total = len(rows)
    print(f"共 {total} 份实习 JD\n")
    print("方向分布:")
    for cat, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"  {cat:<14} {len(items):>3} 条  ({len(items) / total * 100:.0f}%)")

    for cat, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"\n{'=' * 60}\n【{cat}】{len(items)} 条")
        skill = Counter()
        for it in items:
            for name, pat in [
                ("Python", r"python"),
                ("Java", r"java"),
                ("TypeScript/JS", r"typescript|javascript|react|vue"),
                ("LangChain", r"langchain"),
                ("LangGraph", r"langgraph"),
                ("RAG", r"\brag\b|检索增强"),
                ("知识库", r"知识库"),
                ("向量库", r"向量|embedding|faiss|milvus|chroma"),
                ("Function Calling", r"function\s*calling|tool\s*calling|工具调用"),
                ("Multi-Agent", r"multi[- ]?agent|多智能体"),
                ("MCP", r"\bmcp\b"),
                ("Prompt", r"prompt"),
                ("微调", r"微调|fine[- ]?tun|lora"),
                ("PyTorch", r"pytorch"),
                ("FastAPI", r"fastapi"),
                ("Docker", r"docker"),
                ("MySQL", r"mysql|postgres"),
            ]:
                if re.search(pat, it["desc"].lower()):
                    skill[name] += 1
        top = skill.most_common(10)
        print("  高频要求:", "，".join(f"{k} {v}" for k, v in top))
        print("  代表岗位:")
        for it in items[:6]:
            print(f"    {it['title'][:30]:<32} {it['company'][:14]:<16} {it['salary'] or '-'}")

    # 存一份分类结果，供看板使用
    out = {
        "total": total,
        "groups": {
            cat: [
                {"title": i["title"], "company": i["company"], "salary": i["salary"], "url": i["url"]}
                for i in items
            ]
            for cat, items in groups.items()
        },
    }
    with open("data/jd_categories.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\n分类结果已存 data/jd_categories.json")

    conn.close()


if __name__ == "__main__":
    main()
