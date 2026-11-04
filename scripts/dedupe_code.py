"""清理重复的项目代码记录：同一个目录只留一条。

保留规则：优先保留「名字像简历项目」的那条（长度更长、含中文或副标题），
删掉用目录名存的简版。
"""

from __future__ import annotations

import json
import sys

from job_scout.codebase import CODE_DIR, _path_key

APPLY = "--yes" in sys.argv

groups: dict[str, list[dict]] = {}
for p in sorted(CODE_DIR.glob("*.json")):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    key = _path_key(d.get("path", ""))
    groups.setdefault(key, []).append({"file": p, "data": d})

removed = 0
for key, items in groups.items():
    if len(items) <= 1:
        continue
    print(f"\n重复目录: {key}")
    for it in items:
        print(f"  - {it['data'].get('project_name')}  ({it['file'].name})")

    # 保留名字最长的那个（通常是简历里的完整项目名）
    keep = max(items, key=lambda x: len(x["data"].get("project_name", "")))
    print(f"  保留: {keep['data'].get('project_name')}")

    for it in items:
        if it is keep:
            continue
        print(f"  删除: {it['file'].name}")
        if APPLY:
            it["file"].unlink(missing_ok=True)
        removed += 1

print(f"\n{'已删除' if APPLY else '将删除'} {removed} 条")
if not APPLY and removed:
    print("确认要删就加 --yes")
