"""实习岗位专项统计。"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter

c = sqlite3.connect("data/job_scout.db")
c.row_factory = sqlite3.Row

rows = c.execute("SELECT * FROM postings").fetchall()
print("总岗位:", len(rows))
print("有 JD :", sum(1 for r in rows if r["description"]))

INTERN = re.compile(r"实习")


def is_intern(r) -> bool:
    # 严格口径：标题里必须有「实习」
    return bool(INTERN.search(r["title"] or ""))


interns = [r for r in rows if is_intern(r)]
print("实习/应届:", len(interns))

if not interns:
    print("\n还没有实习岗。")
    raise SystemExit(0)

# 薪资
sal = []
for r in interns:
    raw = r["salary_raw"] or ""
    m = re.search(r"(\d+)-(\d+)元/天", raw)
    if m:
        sal.append((int(m.group(1)), int(m.group(2)), "day"))
        continue
    m = re.search(r"(\d+)-(\d+)K", raw)
    if m:
        sal.append((int(m.group(1)), int(m.group(2)), "month"))

day = [s for s in sal if s[2] == "day"]
month = [s for s in sal if s[2] == "month"]
if day:
    lows = sorted(s[0] for s in day)
    print(f"\n日薪岗位: {len(day)} 条  中位 {lows[len(lows) // 2]} 元/天  "
          f"范围 {lows[0]}-{sorted(s[1] for s in day)[-1]}")
if month:
    print(f"月薪岗位: {len(month)} 条")

# 技能
sk = Counter()
for r in interns:
    try:
        for s in json.loads(r["skills"] or "[]"):
            if s:
                sk[s] += 1
    except Exception:
        pass
print("\n实习岗技能 Top12:")
for name, n in sk.most_common(12):
    print(f"   {name:<16} {n}")

# 公司
co = Counter(r["company"] for r in interns if r["company"])
print("\n招聘实习的公司 Top10:")
for name, n in co.most_common(10):
    print(f"   {name:<24} {n}")

# 区域
dist = Counter(r["district"] for r in interns if r["district"])
print("\n区域:")
for name, n in dist.most_common(8):
    print(f"   {name:<8} {n}")

# 样例
print("\n岗位样例（前 25 条）:")
for r in interns[:25]:
    print(f"   {r['title'][:34]:<36} | {r['company'][:14]:<16} | "
          f"{(r['salary_raw'] or '-')[:16]:<18} | {r['district'] or '-'}")

c.close()
