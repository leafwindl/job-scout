"""分析接口原始响应，找岗位类型相关字段。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

p = Path("data/raw/boss_api_capture.json")
if not p.exists():
    raise SystemExit("没有抓包文件")

raw = json.loads(p.read_text(encoding="utf-8"))


def find_job_list(obj, depth=0):
    """在任意结构里找岗位数组。"""
    if depth > 6:
        return None
    if isinstance(obj, dict):
        for v in obj.values():
            r = find_job_list(v, depth + 1)
            if r:
                return r
        return None
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        if any("jobName" in x or "job_name" in x for x in obj[:3]):
            return obj
        for x in obj[:3]:
            r = find_job_list(x, depth + 1)
            if r:
                return r
    return None


jobs = find_job_list(raw)
if not jobs:
    print("没找到岗位数组，顶层结构：")
    print(json.dumps(raw, ensure_ascii=False)[:500])
    raise SystemExit(1)

print(f"岗位样本: {len(jobs)} 条")
print(f"\n=== 字段列表 ===")
keys = sorted(set().union(*(j.keys() for j in jobs)))
print("  " + ", ".join(keys))

print(f"\n=== 可能表示类型的字段 ===")
for k in keys:
    if any(w in k.lower() for w in ("type", "job", "flag", "property", "kind")):
        vals = Counter(str(j.get(k)) for j in jobs[:60])
        if 1 < len(vals) <= 6:
            print(f"  {k}: {dict(vals)}")

print(f"\n=== 前 8 条标题 + jobType 候选 ===")
for j in jobs[:8]:
    title = j.get("jobName") or j.get("job_name")
    parts = [f"{k}={j.get(k)}" for k in keys if "type" in k.lower()]
    print(f"  {title} | " + " ".join(parts))
