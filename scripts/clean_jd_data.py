"""批量清洗数据库里的 JD 正文。"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))

from job_scout.textclean import clean_jd, is_dirty  # noqa: E402

APPLY = "--yes" in sys.argv

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT job_id, title, description FROM postings WHERE description IS NOT NULL"
).fetchall()

dirty = [(r["job_id"], r["title"], r["description"]) for r in rows if is_dirty(r["description"])]
print(f"共 {len(rows)} 条 JD，其中 {len(dirty)} 条需要清洗")

total_before = sum(len(d) for _, _, d in dirty)
total_after = sum(len(clean_jd(d)) for _, _, d in dirty)
print(f"清洗前总字数 {total_before} -> 清洗后 {total_after}（减少 {total_before - total_after}）")

# 抽样对比
for jid, title, desc in dirty[:3]:
    cleaned = clean_jd(desc)
    print(f"\n[{title}]")
    print(f"  前: {desc[:80]!r}")
    print(f"  后: {cleaned[:80]!r}")

if not dirty:
    print("\n没有需要清洗的数据")
    sys.exit(0)

if not APPLY:
    print("\n确认要写入就加 --yes")
    sys.exit(0)

n = 0
for jid, _, desc in dirty:
    conn.execute(
        "UPDATE postings SET description = ? WHERE job_id = ?",
        (clean_jd(desc), jid),
    )
    n += 1
conn.commit()
print(f"\n✓ 已清洗 {n} 条")
