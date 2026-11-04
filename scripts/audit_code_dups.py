"""检查已存项目代码：有没有重复指向同一个目录。"""

from __future__ import annotations

import json
from pathlib import Path

from job_scout.codebase import CODE_DIR

items = []
for p in sorted(CODE_DIR.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    items.append(
        {
            "file": p.name,
            "project_name": d.get("project_name", ""),
            "path": d.get("path", ""),
            "files": d.get("file_count", 0),
            "lines": d.get("line_count", 0),
        }
    )

print(f"共 {len(items)} 条记录\n")
for it in items:
    print(f"  {it['project_name']}")
    print(f"    slug 文件: {it['file']}")
    print(f"    路径: {it['path']}")
    print(f"    规模: {it['files']} 文件 / {it['lines']} 行")
    print()

# 找重复路径
by_path: dict[str, list[str]] = {}
for it in items:
    key = it["path"].rstrip("\\/").lower()
    by_path.setdefault(key, []).append(it["project_name"])

dups = {k: v for k, v in by_path.items() if len(v) > 1}
print("=== 重复路径 ===")
if dups:
    for path, names in dups.items():
        print(f"  {path}")
        for n in names:
            print(f"    - {n}")
else:
    print("  没有重复")
