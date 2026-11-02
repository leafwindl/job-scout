"""按方向导出实习岗位清单（CSV，Excel 可直接打开）。"""

from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from pathlib import Path

from job_scout.classify import classify

OUT = Path("data/exports")
OUT.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT title, company, salary_raw, city, district, experience, url, description, jd_attempts "
    "FROM postings WHERE title LIKE '%实习%'"
).fetchall()

groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
for r in rows:
    cat, _ = classify(r["description"] or "")
    groups[cat].append(r)

# 统一排序：按方向名
for cat in sorted(groups):
    items = sorted(groups[cat], key=lambda r: (r["salary_raw"] or ""), reverse=True)
    path = OUT / f"{cat.replace('/', '_')}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["岗位", "公司", "薪资", "城市", "区域", "经验", "链接", "有JD", "尝试次数"])
        for r in items:
            w.writerow(
                [
                    r["title"],
                    r["company"],
                    r["salary_raw"] or "",
                    r["city"] or "",
                    r["district"] or "",
                    r["experience"] or "",
                    r["url"] or "",
                    "是" if r["description"] else "否",
                    r["jd_attempts"] or 0,
                ]
            )
    print(f"{cat:<16} {len(items):>3} 条 -> {path}")

conn.close()
print(f"\n共 {len(rows)} 条实习岗位，导出到 {OUT.resolve()}")
