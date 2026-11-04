"""重新扫描现有项目，让摘要里用简历项目名而不是目录名。"""

from __future__ import annotations

import json

from job_scout.codebase import CODE_DIR, save_scan, scan_project

items = []
for p in sorted(CODE_DIR.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    items.append((d.get("path", ""), d.get("project_name", "")))

print(f"重新扫描 {len(items)} 个项目\n")
for path, name in items:
    # 路径是容器内格式，转回宿主路径再扫（本地跑时 _to_host_path 不生效）
    host = path.replace("/host/f/", "F:/").replace("/host/c/", "C:/")
    scan = scan_project(host)
    if not scan.ok or scan.file_count == 0:
        print(f"  ✗ {name}: {scan.error or '没找到源码'}")
        continue
    saved = save_scan(scan, name)
    first = (saved["summary"].splitlines() or [""])[0]
    print(f"  ✓ {name[:36]:<38} {first[:40]}")
