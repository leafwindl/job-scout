"""统计 JD 的结构：职责/要求在哪、占多少、前面的公司宣传有多长。"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter

from job_scout.textclean import _JD_CORE_MARKERS

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT job_id, title, description FROM postings WHERE description IS NOT NULL AND description != ''"
).fetchall()
conn.close()

print(f"共 {len(rows)} 条 JD\n")

lens = [len(r["description"] or "") for r in rows]
lens.sort()
print("=== 长度分布 ===")
print(f"  中位数 {lens[len(lens) // 2]} 字　最短 {lens[0]}　最长 {lens[-1]}")
print(f"  >2000 字: {sum(1 for x in lens if x > 2000)} 条")

# 职责/要求标记出现在哪
first_hit: list[int] = []
no_hit = 0
for r in rows:
    text = r["description"] or ""
    pos = -1
    for marker in _JD_CORE_MARKERS:
        p = text.find(marker)
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos == -1:
        no_hit += 1
    else:
        first_hit.append(pos)

first_hit.sort()
print("\n=== 职责/要求标记的位置 ===")
print(f"  找不到标记: {no_hit} 条（{no_hit * 100 // len(rows)}%）")
if first_hit:
    print(f"  找到标记: {len(first_hit)} 条")
    print(f"  标记位置中位数 {first_hit[len(first_hit) // 2]} 字")
    print(f"  标记在开头 100 字内: {sum(1 for x in first_hit if x < 100)} 条")
    print(f"  标记在 500 字之后: {sum(1 for x in first_hit if x > 500)} 条")

# 常见小节标题
print("\n=== 出现的段落标记词 ===")
cnt: Counter[str] = Counter()
for r in rows:
    text = r["description"] or ""
    for m in re.finditer(r"[【\[]([^】\]]{2,10})[】\]]", text):
        cnt[m.group(1)] += 1
for k, v in cnt.most_common(15):
    print(f"  {k}: {v}")

# 抽一条看结构
print("\n=== 样例：开头 300 字 vs 职责段 ===")
longest = max(rows, key=lambda r: len(r["description"] or ""))
text = longest["description"]
print(f"岗位: {longest['title']}  {len(text)} 字")
print(f"  开头: {text[:200]}")
pos = -1
for marker in _JD_CORE_MARKERS:
    p = text.find(marker)
    if p != -1 and (pos == -1 or p < pos):
        pos = p
if pos > 0:
    print(f"  职责段起点 {pos} 字处: {text[pos:pos + 200]}")
