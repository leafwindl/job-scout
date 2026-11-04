"""检查 JD 的结构多样性：标记之后真的有职责列表吗？"""

from __future__ import annotations

import re
import sqlite3

from job_scout.textclean import _JD_CORE_MARKERS

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT title, description FROM postings WHERE description IS NOT NULL"
).fetchall()
conn.close()


def first_marker_pos(text: str) -> int:
    pos = -1
    for m in _JD_CORE_MARKERS:
        p = text.find(m)
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    return pos


def looks_like_list(text: str) -> bool:
    """标记之后有没有列表特征：1、2、●、-、(1)、① 等。"""
    return bool(re.search(r"[1１一][、.．)）]|[●•·\-*]\s|\(\d\)|（\d）|[①②③④⑤]", text))


structured = 0
semi = 0
flat = 0
samples: dict[str, list[tuple[str, str]]] = {"structured": [], "semi": [], "flat": []}

for r in rows:
    text = r["description"] or ""
    pos = first_marker_pos(text)
    if pos == -1:
        flat += 1
        if len(samples["flat"]) < 3:
            samples["flat"].append((r["title"], text[:180]))
        continue
    tail = text[pos : pos + 600]
    if looks_like_list(tail):
        structured += 1
        if len(samples["structured"]) < 2:
            samples["structured"].append((r["title"], tail[:180]))
    else:
        semi += 1
        if len(samples["semi"]) < 3:
            samples["semi"].append((r["title"], tail[:180]))

total = len(rows)
print(f"共 {total} 条\n")
print("=== 结构类型 ===")
print(f"  规范：有标记 + 后面是列表        {structured} 条（{structured * 100 // total}%）")
print(f"  半规范：有标记但后面是段落文字    {semi} 条（{semi * 100 // total}%）")
print(f"  没标记：整段平铺                  {flat} 条（{flat * 100 // total}%）")

for kind, label in (("structured", "规范"), ("semi", "半规范"), ("flat", "无标记")):
    print(f"\n=== {label} 样例 ===")
    for title, text in samples[kind]:
        print(f"  [{title[:26]}]")
        print(f"    {text[:170]}")
        print()
