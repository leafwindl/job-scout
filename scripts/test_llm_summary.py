"""测试 A+B：抽核心文件代码 -> LLM 生成项目介绍。"""

from __future__ import annotations

from job_scout.codebase import build_core_code, render_summary, scan_project, summarize_with_llm
from job_scout.rag.llm import get_llm

PROJECTS = [
    ("F:/Project_do/Agent/job-scout", "AI 求职助手"),
    ("F:/project_work/AI_Chat", "Echo AI 助手 App —— Agent 工具调度与长期记忆"),
]

llm = get_llm()

for path, name in PROJECTS:
    scan = scan_project(path)
    code = build_core_code(scan)
    print("=" * 76)
    print(f"{name}")
    print(f"  扫描: {scan.file_count} 文件 / {scan.line_count} 行")
    print(f"  核心代码: {len(code)} 字")
    for ln in code.splitlines():
        if ln.startswith("### "):
            print(f"    {ln}")

    summary = summarize_with_llm(scan, code, llm)
    print(f"\n  intro: {summary.get('intro')}")
    print(f"  modules: {summary.get('modules')}")
    print(f"  highlights: {summary.get('highlights')}")

    print("\n  --- 最终存进去的摘要 ---")
    print("  " + render_summary(scan, name, summary).replace("\n", "\n  "))
    print()
