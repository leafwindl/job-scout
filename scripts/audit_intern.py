"""数据构成体检：实习 vs 全职、有 JD 比例。"""

from __future__ import annotations

import sqlite3

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row

q = """
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN title LIKE '%实习%' THEN 1 ELSE 0 END) AS intern,
  SUM(CASE WHEN title NOT LIKE '%实习%' THEN 1 ELSE 0 END) AS non_intern,
  SUM(CASE WHEN title LIKE '%实习%' AND description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) AS intern_with_jd,
  SUM(CASE WHEN title NOT LIKE '%实习%' AND description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) AS non_intern_with_jd
FROM postings
"""
r = conn.execute(q).fetchone()
print("=== 总体 ===")
for k in r.keys():
    print(f"  {k}: {r[k]}")

print("\n=== 非实习岗样例（看看混进来什么）===")
rows = conn.execute(
    "SELECT title, company, salary_raw FROM postings "
    "WHERE title NOT LIKE '%实习%' ORDER BY last_seen DESC LIMIT 12"
).fetchall()
for x in rows:
    print(f"  {x['title']} | {x['company']} | {x['salary_raw']}")

print("\n=== 岗位类型关键词分布 ===")
for kw in ("实习", "全职", "校招", "兼职", "应届"):
    n = conn.execute(
        "SELECT COUNT(*) FROM postings WHERE title LIKE ?", (f"%{kw}%",)
    ).fetchone()[0]
    print(f"  {kw}: {n}")

conn.close()
