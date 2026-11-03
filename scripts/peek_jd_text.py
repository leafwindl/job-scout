"""抽样看 JD 原始文本，重点看空格和断行异常。"""

from __future__ import annotations

import sqlite3
import re

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT job_id, title, description, length(description) AS n FROM postings "
    "WHERE description IS NOT NULL AND description != '' "
    "ORDER BY n DESC LIMIT 3"
).fetchall()

for r in rows:
    text = r["description"]
    print("=" * 72)
    print(f"[{r['title']}]  {r['n']} 字")
    print("-" * 72)
    print(text[:600])
    print("-" * 72)
    # 统计异常空格
    dbl = len(re.findall(r"  +", text))
    cjk_space = len(re.findall(r"[\u4e00-\u9fff] +[\u4e00-\u9fff]", text))
    print(f"  连续空格: {dbl} 处 | 中文之间的空格: {cjk_space} 处")
    # 展示前 3 处中文间空格上下文
    for m in list(re.finditer(r"[\u4e00-\u9fff] +[\u4e00-\u9fff]", text))[:3]:
        s = max(0, m.start() - 12)
        print(f"    …{text[s:m.end()+12]!r}")
    print()

conn.close()
