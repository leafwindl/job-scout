"""用新的 LLM 摘要跑一次对照审查，看看质量。"""

from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8001"

req = urllib.request.Request(
    BASE + "/code/review",
    data=json.dumps({"project": "Echo AI 助手 App —— Agent 工具调度与长期记忆"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=600) as r:
    d = json.loads(r.read().decode())

print(f"项目: {d['project']}\n")
print(f"判断: {d['verdict']}\n")
print(f"和代码不符 {len(d['inaccurate'])} 条 / 遗漏 {len(d['missing'])} 条 / 改写 {len(d['rewrites'])} 条\n")

for x in d["inaccurate"][:2]:
    print(f"  ⚠ 简历: {x['claim'][:60]}")
    print(f"     代码: {x['reality'][:70]}")
    print(f"     改:   {x['fix'][:70]}\n")

for x in d["missing"][:3]:
    print(f"  + 代码: {x['fact'][:70]}")
    print(f"    可补: {x['suggest'][:80]}\n")
