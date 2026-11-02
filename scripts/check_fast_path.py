"""验证 deep=False 是毫秒级返回。"""

from __future__ import annotations

import time

from job_scout.company import build_company_profile, prep_analysis
from job_scout.profile import load_profile

t = time.time()
d = build_company_profile("安点科技", None, deep=False)
print(f"company deep=False: {(time.time() - t) * 1000:.0f}ms | 字段 {len(d)} | 有 business: {'business' in d}")

p = load_profile()
t = time.time()
r = prep_analysis(p, None, deep=False)
print(f"prep    deep=False: {(time.time() - t) * 1000:.0f}ms | 缺口 {len(r['missing'])} 项 | 有 overview: {'overview' in r}")
