"""JD 正文技术词报告。"""

from __future__ import annotations

from job_scout.dashboard import build_payload, load_postings

p = build_payload(load_postings("data/job_scout.db"))
total = p["total"]
jd_total = p["jd_total"]

print(f"实习岗位 {total} 条，其中有 JD 正文 {jd_total} 条")
print(f"薪资中位数 {p['median_k']}K\n")

print("JD 正文技术词（提及岗位数 / 占 JD 比例）:")
for name, n in p["jd_keywords"]:
    pct = round(n / jd_total * 100) if jd_total else 0
    bar = "█" * max(1, round(pct / 3))
    print(f"  {name:<16} {n:>3}  {pct:>3}%  {bar}")

print("\n薪资分布:")
for k, v in p["salary_buckets"].items():
    print(f"  {k:<8} {v}")

print("\n经验要求:")
for name, n in p["experience"][:8]:
    print(f"  {name:<10} {n}")

print("\n区域:")
for name, n in p["districts"][:8]:
    print(f"  {name:<8} {n}")

print("\n招聘最多的公司:")
for name, n in p["companies"][:10]:
    print(f"  {name:<26} {n}")
