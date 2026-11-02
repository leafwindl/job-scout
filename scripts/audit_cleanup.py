"""数据库体检：清理前看清楚每一类有多少。"""

from __future__ import annotations

import sqlite3

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row


def q(sql: str) -> int:
    return conn.execute(sql).fetchone()[0]


total = q("SELECT COUNT(*) FROM postings")
print(f"=== 总计 {total} 条 ===\n")

print("按类型：")
intern = q("SELECT COUNT(*) FROM postings WHERE title LIKE '%实习%'")
print(f"  实习        {intern}")
print(f"  非实习      {total - intern}")

print("\n按相关性：")
rel = q("SELECT COUNT(*) FROM postings WHERE is_relevant = 1")
print(f"  相关        {rel}")
print(f"  无关        {total - rel}")

print("\n按状态：")
active = q("SELECT COUNT(*) FROM postings WHERE is_active = 1")
print(f"  在架        {active}")
print(f"  停招        {total - active}")

print("\n按 JD：")
jd = q("SELECT COUNT(*) FROM postings WHERE description IS NOT NULL AND description != ''")
print(f"  有 JD       {jd}")
print(f"  无 JD       {total - jd}")

print("\n=== 核心保留集（实习 + 相关 + 在架）===")
keep = q(
    "SELECT COUNT(*) FROM postings "
    "WHERE title LIKE '%实习%' AND is_relevant = 1 AND is_active = 1"
)
keep_jd = q(
    "SELECT COUNT(*) FROM postings "
    "WHERE title LIKE '%实习%' AND is_relevant = 1 AND is_active = 1 "
    "AND description IS NOT NULL AND description != ''"
)
print(f"  {keep} 条，其中 {keep_jd} 条有 JD")

print("\n=== 待清理 ===")
print(f"  非实习              {total - intern}")
print(f"  无关标题            {total - rel}")
both = q("SELECT COUNT(*) FROM postings WHERE title NOT LIKE '%实习%' OR is_relevant = 0")
print(f"  两者至少一个        {both}")
print(f"  停招                {total - active}")

print("\n=== 清理后剩余 ===")
print(f"  {keep} 条（全部保留）")

print("\n=== 保留集里的方向分布（抽样）===")
rows = conn.execute(
    "SELECT title FROM postings "
    "WHERE title LIKE '%实习%' AND is_relevant = 1 AND is_active = 1 "
    "ORDER BY last_seen DESC LIMIT 12"
).fetchall()
for r in rows:
    print(f"  {r['title']}")

conn.close()
