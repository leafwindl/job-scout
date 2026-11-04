"""测试目录浏览与项目自动发现。"""

from __future__ import annotations

from job_scout.codebase import browse_dir, discover_projects


def show(path: str) -> None:
    d = browse_dir(path)
    print(f"路径: {d.get('path')}  子目录 {len(d.get('dirs', []))} 个")
    if d.get("error"):
        print(f"  错误: {d['error']}")
        return
    for x in d.get("dirs", [])[:12]:
        mark = "[项目]" if x["is_project"] else "      "
        print(f"  {mark} {x['name']}")


show("F:/project_work")
print()
show("F:/Project_do")

print("\n=== 自动发现 F:/project_work 下的项目 ===")
ps = discover_projects("F:/project_work")
print(f"发现 {len(ps)} 个：")
for x in ps:
    print(f"  · {x['name']}   标志文件={x['markers']}  源码={x['code_files']}")

print("\n=== 自动发现 F:/Project_do/Agent 下的项目 ===")
ps2 = discover_projects("F:/Project_do/Agent")
print(f"发现 {len(ps2)} 个：")
for x in ps2:
    print(f"  · {x['name']}   标志文件={x['markers']}")
