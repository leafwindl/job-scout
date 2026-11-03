"""测试「结合简历」的问答效果。"""

from __future__ import annotations

from job_scout.profile import build_profile_text, load_profile
from job_scout.rag.pipeline import get_pipeline

pipe = get_pipeline()
profile = load_profile()
pt = build_profile_text(profile)
print(f"简历摘要 {len(pt)} 字\n")

QUESTIONS = [
    "结合我的简历，我适合投哪些岗位？为什么？",
    "我的 Echo AI 助手项目，能对上哪些岗位的要求？",
]

for q in QUESTIONS:
    print("=" * 68)
    print(f"问: {q}\n")
    a = pipe.ask(q, k=5, profile_text=pt)
    print(f"[用时模式 {a.mode}｜引用 {len(a.citations)} 条]")
    print(a.text[:900])
    print()
