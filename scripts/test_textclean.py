"""测试 JD 清洗效果。"""

from __future__ import annotations

import sqlite3

from job_scout.textclean import clean_jd, is_dirty

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT job_id, title, description FROM postings WHERE description IS NOT NULL"
).fetchall()
conn.close()

dirty = [r for r in rows if is_dirty(r["description"])]
print(f"需要清洗: {len(dirty)}/{len(rows)} 条\n")

if dirty:
    r = max(dirty, key=lambda x: len(x["description"]))
    before = r["description"]
    after = clean_jd(before)
    print(f"样例 [{r['title']}]")
    print(f"  清洗前 {len(before)} 字 -> 清洗后 {len(after)} 字")
    print("  清洗后前 240 字:")
    print("  " + after[:240].replace("\n", " "))
    print(f"  清洗后仍需清洗: {is_dirty(after)}")

    print("\n水印残留检查:")
    for w in ("kanzhun", "boss", "直聘", "{", "display:none"):
        print(f"  {w!r}: {'有' if w in after else '无'}")
