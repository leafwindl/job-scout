"""看实习岗位里到底混进了什么。"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))
from job_scout.classify import classify  # noqa: E402

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT job_id, title, company, skills, description FROM postings "
    "WHERE title LIKE '%实习%' AND is_active = 1"
).fetchall()

print(f"在架实习岗: {len(rows)} 条\n")

# 分类分布
cats = Counter()
labels = []
for r in rows:
    text = (r["description"] or "") or (r["title"] or "")
    cat, _ = classify(text)
    cats[cat] += 1
    labels.append((r["title"], cat, r["company"]))

print("=== 方向分布 ===")
for k, v in cats.most_common():
    print(f"  {k}: {v}")

# 标题里有没有 Agent / AI 关键词
KEY = ["agent", "ai", "大模型", "llm", "rag", "机器学习", "算法", "智能", "算力", "nlp"]
hit = 0
miss = []
for t, cat, co in labels:
    low = (t or "").lower()
    if any(k in low for k in KEY):
        hit += 1
    else:
        miss.append((t, cat, co))

print(f"\n=== 标题命中 AI/Agent 关键词: {hit}/{len(labels)} ===")
print(f"\n=== 未命中的 {len(miss)} 条（前 25）===")
for t, cat, co in miss[:25]:
    print(f"  {t} | {co} | {cat}")
conn.close()
