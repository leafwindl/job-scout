"""测试公司画像 + 技术准备。"""

from __future__ import annotations

from job_scout.company import build_company_profile, list_companies, prep_analysis
from job_scout.profile import load_profile
from job_scout.rag.llm import get_llm

llm = get_llm()
cos = list_companies(2)
print(f"有 2+ 岗位的公司: {len(cos)} 家")
for c in cos[:5]:
    print(f"  {c['company']}  {c['jobs']} 条  {c['districts']}")

if cos:
    target = cos[0]["company"]
    print(f"\n{'='*64}\n公司画像: {target}")
    p = build_company_profile(target, llm)
    print(f"  业务: {p.get('business')}")
    print(f"  技术风格: {p.get('tech_style')}")
    print(f"  团队: {p.get('team')}")
    print(f"  什么人吃香: {p.get('person_fit')}")
    print(f"  面试可能问: {p.get('interview_focus')}")
    print(f"  结论: {p.get('verdict')}")
    print(f"  信号: {list(p.get('signals', {}).items())[:5]}")
    print(f"  技能: {[s['name'] for s in p.get('skills', [])[:8]]}")

profile = load_profile()
if profile:
    print(f"\n{'='*64}\n技术准备")
    r = prep_analysis(profile, llm)
    print(f"  范围: {r.get('scope')}")
    print(f"  概览: {r.get('overview')}")
    print("  要补:")
    for x in r.get("learn") or []:
        print(f"    · {x.get('skill')} — {x.get('why')}")
        print(f"      怎么学: {x.get('how')}")
    print("  可放大:")
    for x in r.get("leverage") or []:
        print(f"    + {x}")
    print("  可跳过:")
    for x in r.get("skip") or []:
        print(f"    - {x}")
