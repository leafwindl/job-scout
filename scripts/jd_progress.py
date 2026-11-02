"""实习岗 JD 抓取进度。"""

from __future__ import annotations

import sqlite3

c = sqlite3.connect("data/job_scout.db")

TOTAL = "SELECT COUNT(*) FROM postings"
INTERN = "SELECT COUNT(*) FROM postings WHERE title LIKE '%实习%'"
HAS_JD = "SELECT COUNT(*) FROM postings WHERE description IS NOT NULL AND description != ''"
INTERN_HAS = (
    "SELECT COUNT(*) FROM postings WHERE title LIKE '%实习%' "
    "AND description IS NOT NULL AND description != ''"
)

print("全部岗位      :", c.execute(TOTAL).fetchone()[0])
print("其中实习      :", c.execute(INTERN).fetchone()[0])
print("全部有 JD     :", c.execute(HAS_JD).fetchone()[0])
print("实习有 JD     :", c.execute(INTERN_HAS).fetchone()[0])

rows = c.execute(
    "SELECT COUNT(*), AVG(LENGTH(description)), MIN(LENGTH(description)), MAX(LENGTH(description)) "
    "FROM postings WHERE title LIKE '%实习%' AND description IS NOT NULL AND description != ''"
).fetchone()
print(f"实习 JD 平均字数: {round(rows[1]) if rows[1] else 0}  "
      f"最短 {rows[2] or 0}  最长 {rows[3] or 0}")

print("\n最近有 JD 的 5 条:")
for r in c.execute(
    "SELECT title, company, LENGTH(description) n FROM postings "
    "WHERE title LIKE '%实习%' AND description IS NOT NULL AND description != '' "
    "ORDER BY last_seen DESC LIMIT 5"
):
    print(f"  {r[0][:30]:<32} {r[1][:14]:<16} {r[2]} 字")

c.close()
