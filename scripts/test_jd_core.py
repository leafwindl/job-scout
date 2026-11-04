"""测试 JD 核心段提取：是不是只剩职责和要求。"""

from __future__ import annotations

import sqlite3

from job_scout.textclean import extract_jd_core

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT title, description FROM postings "
    "WHERE description IS NOT NULL AND length(description) > 1500 "
    "ORDER BY length(description) DESC LIMIT 3"
).fetchall()
conn.close()

for r in rows:
    jd = r["description"] or ""
    core = extract_jd_core(jd, 900)
    print("=" * 74)
    print(f"{r['title']}")
    print(f"  原 JD {len(jd)} 字  ->  核心 {len(core)} 字（压缩 {100 - len(core)*100//max(1,len(jd))}%）")
    print(f"  开头: {core[:160]}")
    print()
