"""检查已抓到的 JD 正文质量。"""

from __future__ import annotations

import sqlite3

c = sqlite3.connect("data/job_scout.db")
c.row_factory = sqlite3.Row

rows = c.execute(
    "SELECT title, company, url, description FROM postings WHERE description IS NOT NULL AND description <> ''"
).fetchall()

print("有正文的:", len(rows))
for r in rows[:10]:
    d = r["description"] or ""
    print(f"\n{r['title'][:30]} | {r['company'][:14]}")
    print(f"  长度: {len(d)}")
    print(f"  开头: {d[:140]}")
    print(f"  url : {(r['url'] or '')[:90]}")

print("\n长度分布:")
lens = sorted(len(r["description"] or "") for r in rows)
if lens:
    print("  最短", lens[0], "中位", lens[len(lens) // 2], "最长", lens[-1])

c.close()
