"""检查停招标记会命中多少条（只读）。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row

for days in (1, 3, 7):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    n = conn.execute(
        "SELECT COUNT(*) FROM postings WHERE last_seen < ? AND is_active = 1",
        (cutoff,),
    ).fetchone()[0]
    print(f"  超过 {days} 天没出现: {n} 条")

print("\n=== last_seen 分布 ===")
rows = conn.execute(
    "SELECT substr(last_seen,1,10) AS d, COUNT(*) c FROM postings "
    "GROUP BY d ORDER BY d DESC LIMIT 8"
).fetchall()
for r in rows:
    print(f"  {r['d']}: {r['c']} 条")

print("\n=== is_active 现状 ===")
for r in conn.execute("SELECT is_active, COUNT(*) c FROM postings GROUP BY is_active"):
    print(f"  is_active={r['is_active']}: {r['c']} 条")

print(f"\n=== 现在时间 ===")
print(f"  {datetime.now().isoformat(timespec='seconds')}")
conn.close()
