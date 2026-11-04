"""诊断：为什么只选中一个项目？"""

from __future__ import annotations

import sqlite3

from job_scout.codebase import get_context, list_saved
from job_scout.profile import load_profile

profile = load_profile()
resume_names = [(x.get("name") or "").strip() for x in profile.projects]

print("简历项目 vs 代码记录:")
saved = {x["project_name"]: x for x in list_saved()}
for n in resume_names:
    hit = "✓" if n in saved else "✗"
    ctx = get_context(n, max_chars=6000)
    print(f"  {hit} {n[:40]:<42} context {len(ctx)} 字")

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT description FROM postings WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
).fetchone()
conn.close()
jd = row["description"] or ""

from job_scout.codebase import _tokens

jd_tokens = _tokens(jd)
print(f"\nJD 分出的 token: {len(jd_tokens)} 个")

for n in resume_names:
    ctx = get_context(n, max_chars=6000)
    if not ctx:
        continue
    total = 0
    hits_overlap = set()
    for ln in ctx.splitlines():
        o = _tokens(ln) & jd_tokens
        total += len(o)
        hits_overlap |= o
    sample = list(hits_overlap)[:8]
    print(f"  {n[:34]:<36} 得分 {total:>4}  命中 {sample}")
