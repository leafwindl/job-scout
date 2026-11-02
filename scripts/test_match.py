"""测试岗位匹配：拿几条真实岗位跑匹配打分。"""

from __future__ import annotations

import sqlite3

from job_scout.profile import load_profile, match_job
from job_scout.rag.llm import get_llm

profile = load_profile()
if profile is None:
    raise SystemExit("先上传/生成画像")

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT job_id, title, company, description FROM postings "
    "WHERE title LIKE '%实习%' AND is_relevant = 1 AND description IS NOT NULL "
    "ORDER BY RANDOM() LIMIT 2"
).fetchall()
conn.close()

llm = get_llm()
for r in rows:
    print("=" * 62)
    print(f"岗位: {r['title']} ｜ {r['company']}")
    m = match_job(profile, r["title"], r["company"], r["description"], llm)
    print(f"  分数: {m['score']}   结论: {m['verdict']}")
    print(f"  理由: {m['reason']}")
    print("  匹配点:")
    for x in (m["matched"] or [])[:3]:
        print(f"    + {x}")
    print("  缺口:")
    for x in (m["missing"] or [])[:3]:
        print(f"    - {x}")
