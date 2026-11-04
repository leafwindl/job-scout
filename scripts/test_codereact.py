"""测试 codereact 两个场景：预扫描（20 轮）和按岗位分析（12 轮）。"""

from __future__ import annotations

import sqlite3

from job_scout.codebase import scan_project
from job_scout.codereact import analyze_for_job, prescan_project
from job_scout.rag.llm import get_llm

llm = get_llm()
if llm is None:
    raise SystemExit("没 Key")

ROOT = "F:/Project_do/Agent/job-scout"
NAME = "AI 求职助手"
scan = scan_project(ROOT)

print("=" * 78)
print("场景一：预扫描（20 轮）")
print("=" * 78)
r1 = prescan_project(ROOT, NAME, scan.tree, llm, max_turns=20)
print(f"轮次 {r1.turns}　调用 {r1.tool_calls}　读文件 {r1.files_read}　"
      f"耗时 {r1.elapsed:.1f}s　上下文 {r1.context_chars}")
if r1.error:
    print("错误:", r1.error)
print()
print(r1.text[:2400])

print()
print("=" * 78)
print("场景二：按岗位分析（12 轮）")
print("=" * 78)

# 拿一条真实 JD
from job_scout.textclean import extract_jd_core

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT title, company, description FROM postings WHERE is_relevant=1 AND description IS NOT NULL LIMIT 1"
).fetchone()
conn.close()
jd_core = extract_jd_core(row["description"] or "", 900)
print(f"岗位：{row['title']} ｜ {row['company']}")

project_desc = """Echo AI 助手 App —— Agent 工具调度与长期记忆
- 基于工具注册表实现 Agent 工具调用机制，接入 6 个工具
- 实现异步消息处理链路，SSE 推送
- 设计记忆抽取与召回链路，pgvector 存储"""

r2 = analyze_for_job(ROOT, "AI 求职助手", scan.tree, jd_core, project_desc, llm, max_turns=12)
print(f"\n轮次 {r2.turns}　调用 {r2.tool_calls}　读文件 {r2.files_read}　"
      f"耗时 {r2.elapsed:.1f}s　上下文 {r2.context_chars}")
if r2.error:
    print("错误:", r2.error)
print()
print(r2.text[:2400])
