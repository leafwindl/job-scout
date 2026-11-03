"""对比 RAG 版简历的 PDF 原文与解析出的 profile.json。"""

from __future__ import annotations

import json
from pathlib import Path

from job_scout.profile import extract_pdf_text

PDF = Path(r"C:\Users\leafwind\Documents\work\叶旭景-广州大学-硕士2026-RAG实习.pdf")

print("=" * 70)
print("PDF 原文")
print("=" * 70)
if PDF.exists():
    text = extract_pdf_text(PDF)
    print(f"字符数: {len(text)}\n")
    print(text)
else:
    print("找不到文件")

print("\n" + "=" * 70)
print("profile.json")
print("=" * 70)
d = json.loads(Path("data/profile.json").read_text(encoding="utf-8"))
print(f"姓名: {d.get('name')}")
print(f"意向: {d.get('target')}")
print(f"教育: {d.get('education')}")
print(f"\n技能({len(d.get('skills') or [])}): {', '.join(d.get('skills') or [])}")
print(f"\n项目({len(d.get('projects') or [])}):")
for x in d.get("projects") or []:
    print(f"  · {x.get('name')}  |  period={x.get('period')!r}  tech={x.get('tech')}")
    for b in (x.get("bullets") or [])[:2]:
        print(f"      - {b[:60]}")
print(f"\n实习({len(d.get('experience') or [])}):")
for x in d.get("experience") or []:
    print(f"  · {x.get('company')} / {x.get('role')}")
