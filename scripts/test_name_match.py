"""测试简历项目名与代码项目名的模糊匹配。"""

from __future__ import annotations

from job_scout.profile import _find_project, load_profile

p = load_profile()

cases = [
    "AI 求职助手",
    "AI_Chat",
    "智能测试全流程平台",
    "庆园 AI 小警",
    "完全不相干的名字",
]

for q in cases:
    r = _find_project(p, q)
    name = r.get("name") or "（没匹配到）"
    print(f"  {q!r:22} -> {name}")
