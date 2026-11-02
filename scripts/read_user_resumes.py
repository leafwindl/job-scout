"""解析用户的两份真实简历（先看文本提取质量）。"""

from __future__ import annotations

from pathlib import Path

from job_scout.profile import extract_pdf_text

FILES = [
    Path(r"C:\Users\leafwind\Documents\work\叶旭景-广州大学-硕士2026-Agent实习.pdf"),
    Path(r"C:\Users\leafwind\Documents\work\叶旭景-广州大学-硕士2026-RAG实习.pdf"),
]

for f in FILES:
    print("=" * 70)
    print(f"文件: {f.name}  存在: {f.exists()}")
    if not f.exists():
        continue
    text = extract_pdf_text(f)
    print(f"提取字符数: {len(text)}")
    print("-" * 70)
    print(text[:2500])
    print()
