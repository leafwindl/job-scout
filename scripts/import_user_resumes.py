"""把用户的两份真实简历解析成画像，各存一份。"""

from __future__ import annotations

import json
from pathlib import Path

from job_scout.profile import (
    Profile,
    extract_pdf_text,
    parse_profile,
    save_profile,
)
from job_scout.rag.llm import get_llm

FILES = {
    "agent": Path(r"C:\Users\leafwind\Documents\work\叶旭景-广州大学-硕士2026-Agent实习.pdf"),
    "rag": Path(r"C:\Users\leafwind\Documents\work\叶旭景-广州大学-硕士2026-RAG实习.pdf"),
}

llm = get_llm()
out_dir = Path("data/resume")
out_dir.mkdir(parents=True, exist_ok=True)

for variant, path in FILES.items():
    if not path.exists():
        print(f"跳过（不存在）: {path}")
        continue

    text = extract_pdf_text(path)
    p = parse_profile(text, llm)
    p.source_file = path.name

    # 存一份带 variant 后缀的
    dest = out_dir / f"profile_{variant}.json"
    dest.write_text(
        json.dumps(p.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 66)
    print(f"[{variant}] {path.name}")
    print(f"  姓名: {p.name}  意向: {p.target or '（未写）'}")
    print(f"  技能 {len(p.skills)} 项: {', '.join(p.skills[:14])}")
    print(f"  项目 {len(p.projects)} 个:")
    for proj in p.projects:
        print(f"    - {proj.get('name')}  要点 {len(proj.get('bullets') or [])} 条")
    print(f"  教育: {p.education}")
    print(f"  已存: {dest}")

# 默认画像用 agent 版（更全面）
agent_json = out_dir / "profile_agent.json"
if agent_json.exists():
    data = json.loads(agent_json.read_text(encoding="utf-8"))
    save_profile(Profile.from_dict(data))
    print("\n默认画像已设为 agent 版 -> data/profile.json")
