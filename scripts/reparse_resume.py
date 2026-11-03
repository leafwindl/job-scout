"""用改进后的 prompt 重新解析 RAG 版简历，检查 bullets 是否保留细节。"""

from __future__ import annotations

import json
from pathlib import Path

from job_scout.profile import extract_pdf_text, parse_profile
from job_scout.rag.llm import get_llm

PDF = Path(r"C:\Users\leafwind\Documents\work\叶旭景-广州大学-硕士2026-RAG实习.pdf")

text = extract_pdf_text(PDF)
llm = get_llm()
p = parse_profile(text, llm)

print(f"姓名: {p.name}")
print(f"项目数: {len(p.projects)}")
for proj in p.projects:
    print(f"\n【{proj.get('name')}】")
    if proj.get("summary"):
        print(f"  简述: {proj['summary'][:80]}")
    bullets = proj.get("bullets") or []
    print(f"  工作内容 {len(bullets)} 条:")
    for b in bullets:
        print(f"    · {b}")

# 存一份供对比
Path("data/resume/profile_rag_reparsed.json").write_text(
    json.dumps(p.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\n已存 data/resume/profile_rag_reparsed.json")
