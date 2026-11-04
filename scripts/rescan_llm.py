"""用 LLM 重扫现有项目，让摘要变成真介绍。"""

from __future__ import annotations

import json

from job_scout.codebase import CODE_DIR, save_scan, scan_project
from job_scout.rag.llm import get_llm

llm = get_llm()
if llm is None:
    raise SystemExit("没配置模型 Key，无法生成 LLM 摘要")

items = []
for p in sorted(CODE_DIR.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    items.append((d.get("path", ""), d.get("project_name", "")))

print(f"重扫 {len(items)} 个项目（每个约 20 秒）\n")
for path, name in items:
    host = path.replace("/host/f/", "F:/").replace("/host/c/", "C:/")
    scan = scan_project(host)
    if not scan.ok or scan.file_count == 0:
        print(f"  ✗ {name}: {scan.error or '没找到源码'}")
        continue
    saved = save_scan(scan, name, llm=llm)

    s = saved.get("llm_summary") or {}
    cores = saved.get("core_files") or []
    print(f"  ✓ {name[:34]}")
    print(f"      核心文件 {len(cores)} 个: {cores[:3]}")
    intro = (s.get("intro") or "")[:110]
    print(f"      介绍: {intro}…")
    print()
