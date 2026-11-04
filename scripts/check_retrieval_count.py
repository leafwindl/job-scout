"""看检索层到底返回几条。"""

from __future__ import annotations

from job_scout.rag.generate import build_context
from job_scout.rag.pipeline import get_pipeline

pipe = get_pipeline()

for q in ["广州有哪些 Agent 相关实习岗？", "Python 实习"]:
    print(f"问: {q}")
    for k in (5, 8, 12):
        hits = pipe.retriever.search(q, k=k)
        docs = [d for d, _ in hits]
        ctx, used = build_context(docs, max_chars=16000)
        print(f"  k={k:2d}: 检索返回 {len(docs)} 条 -> 上下文装入 {len(used)} 条")
        if k == 8:
            for i, d in enumerate(docs, 1):
                desc = (d.text.split("\n", 1)[-1] or "").strip()
                print(f"        [{i}] {d.title[:26]}  JD {len(desc)} 字")
    print()
