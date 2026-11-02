"""实验：从 JD 里挖「公司隐含倾向」，看能挖出什么。"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT title, company, description, skills, salary_raw, district FROM postings "
    "WHERE title LIKE '%实习%' AND is_relevant = 1 AND description IS NOT NULL"
).fetchall()

# 按公司聚合
by_co: dict[str, list[sqlite3.Row]] = {}
for r in rows:
    by_co.setdefault(r["company"], []).append(r)

print(f"共 {len(rows)} 条岗位，{len(by_co)} 家公司\n")

top = sorted(by_co.items(), key=lambda x: -len(x[1]))[:6]
print("=== 岗位最多的公司 ===")
for co, jobs in top:
    print(f"  {co}: {len(jobs)} 条  [{jobs[0]['district']}]")

# 隐含信号词表
SIGNALS = {
    "从0到1": ["0到1", "从零", "搭建", "建设", "从无到有"],
    "业务贴近": ["业务", "场景", "需求方", "客户", "落地"],
    "工程化": ["工程", "架构", "性能", "部署", "上线", "高并发"],
    "算法研究": ["论文", "顶会", "发表", "研究", "实验", "benchmark"],
    "开源": ["开源", "github", "社区", "贡献"],
    "产品思维": ["产品", "用户体验", "需求分析", "原型"],
    "数据驱动": ["数据", "指标", "ab test", "实验设计", "分析"],
    "团队协作": ["团队", "协作", "沟通", "跨部门"],
}

print("\n=== 各公司的隐含倾向信号（JD 命中次数）===")
for co, jobs in top:
    text = " ".join((j["description"] or "") for j in jobs).lower()
    hits = {k: sum(text.count(w) for w in ws) for k, ws in SIGNALS.items()}
    top_signals = sorted(hits.items(), key=lambda x: -x[1])[:4]
    print(f"\n  【{co}】{len(jobs)} 条")
    print(f"    {'  '.join(f'{k}={v}' for k, v in top_signals if v > 0)}")
    # 技术栈
    skills = Counter()
    for j in jobs:
        for s in (j["skills"] or "").lower().replace("[", "").replace("]", "").replace('"', "").split(","):
            s = s.strip()
            if s:
                skills[s] += 1
    if skills:
        print(f"    技能: {', '.join(f'{k}({v})' for k, v in skills.most_common(5))}")

conn.close()
