"""把生成招呼语时的真实 prompt 打出来（脱敏：只展示结构）。"""

from __future__ import annotations

import sqlite3

from job_scout.codebase import relevant_code_context
from job_scout.profile import (
    GREET_PROMPT,
    build_profile_text,
    load_profile,
    match_job,
)
from job_scout.rag.llm import get_llm

profile = load_profile()
llm = get_llm()

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT job_id, title, company, description FROM postings "
    "WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
).fetchone()
conn.close()

print("=" * 78)
print("第 1 步：先调一次 LLM 算匹配度（match_job）")
print("=" * 78)
m = match_job(profile, row["title"] or "", row["company"] or "", row["description"] or "", llm)
print(f"  分数 {m['score']}｜判断 {m['verdict']}")
print(f"  匹配点 {len(m['matched'])} 条 / 缺口 {len(m['missing'])} 条")

extra = ""
if m["matched"]:
    extra = " 可强调：" + "；".join(m["matched"][:2])
print(f"  → 拼进 extra：{extra[:120]}")

print()
print("=" * 78)
print("第 2 步：按 JD 检索相关代码片段（不走 LLM，纯本地打分）")
print("=" * 78)
resume_names = [(x.get("name") or "").strip() for x in profile.projects]
code_ctx = relevant_code_context(row["description"] or "", only_projects=resume_names,
                                 max_chars=2500)
print(f"  {len(code_ctx)} 字")

print()
print("=" * 78)
print("第 3 步：组装 prompt")
print("=" * 78)

profile_part = build_profile_text(profile)
jd_part = (row["description"] or "")[:2000]
prompt = GREET_PROMPT.format(
    profile=profile_part,
    title=row["title"] or "",
    company=row["company"] or "",
    jd=jd_part,
    code=code_ctx,
    extra=extra or "无",
)

print(f"  prompt 总长 {len(prompt)} 字")
print(f"    简历部分    {len(profile_part)} 字")
print(f"    JD 部分     {len(jd_part)} 字")
print(f"    代码部分    {len(code_ctx)} 字")
print(f"    固定规则    {len(prompt) - len(profile_part) - len(jd_part) - len(code_ctx)} 字")

print()
print("-" * 78)
print("完整 prompt：")
print("-" * 78)
print(prompt)
