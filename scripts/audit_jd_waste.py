"""检查：不相关标题的岗位有多少被拉了 JD。"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))
from job_scout.constants import title_relevant  # noqa: E402

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT title, company, description, is_active FROM postings"
).fetchall()

rel_total = rel_jd = irr_total = irr_jd = 0
irr_samples = []

for r in rows:
    has_jd = bool((r["description"] or "").strip())
    if title_relevant(r["title"]):
        rel_total += 1
        if has_jd:
            rel_jd += 1
    else:
        irr_total += 1
        if has_jd:
            irr_jd += 1
            if len(irr_samples) < 15:
                irr_samples.append((r["title"], r["company"], len(r["description"])))

print(f"标题相关: {rel_total} 条，其中 {rel_jd} 条有 JD")
print(f"标题无关: {irr_total} 条，其中 {irr_jd} 条有 JD  ← 这些是白拉的")
print(f"\n浪费比例: {irr_jd / max(1, rel_jd + irr_jd) * 100:.0f}% 的 JD 抓给了无关岗位")

print(f"\n=== 无关但抓了 JD 的样例 ===")
for t, c, n in irr_samples:
    print(f"  {t} | {c} | {n} 字")

# 待抓里有多少是无关的
pend = conn.execute(
    "SELECT title FROM postings WHERE description IS NULL OR description = ''"
).fetchall()
p_rel = sum(1 for p in pend if title_relevant(p["title"]))
print(f"\n待抓 {len(pend)} 条，其中 {len(pend) - p_rel} 条标题无关（导航会白跑）")

conn.close()
