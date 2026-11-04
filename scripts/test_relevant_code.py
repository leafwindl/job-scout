"""测试「按 JD 检索项目代码」的效果。"""

from __future__ import annotations

import sqlite3

from job_scout.codebase import relevant_code_context
from job_scout.profile import load_profile

profile = load_profile()
resume_names = [(x.get("name") or "").strip() for x in profile.projects]

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT title, description FROM postings "
    "WHERE description IS NOT NULL AND is_relevant=1 LIMIT 3"
).fetchall()
conn.close()

for row in rows:
    jd = row["description"] or ""
    print("=" * 72)
    print(f"岗位: {row['title']}")
    print(f"JD {len(jd)} 字")

    ctx = relevant_code_context(jd, only_projects=resume_names, max_chars=2000)
    print(f"\n检索到的代码片段 {len(ctx)} 字:")
    for ln in ctx.splitlines()[:14]:
        print(f"  {ln[:100]}")
    print()
