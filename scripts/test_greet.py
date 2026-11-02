"""测试打招呼消息生成。"""

from __future__ import annotations

import sqlite3

from job_scout.profile import generate_greeting, load_profile
from job_scout.rag.llm import get_llm

profile = load_profile()
if profile is None:
    raise SystemExit("没有画像")

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
    msg = generate_greeting(profile, r["title"], r["company"], r["description"], llm)
    print(f"\n【招呼语】（{len(msg)} 字）\n{msg}\n")
