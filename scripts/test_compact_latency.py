"""测精简简历摘要后的首 token 延迟。"""

from __future__ import annotations

import time

from job_scout.profile import build_profile_text, load_profile
from job_scout.rag.pipeline import get_pipeline

pipe = get_pipeline()
profile = load_profile()
compact = build_profile_text(profile, compact=True)
full = build_profile_text(profile)
print(f"摘要: 完整 {len(full)} 字 / 精简 {len(compact)} 字\n")

q = "我适合投哪些岗位？"

for label, pt in (("精简", compact), ("完整", full)):
    t0 = time.time()
    first = None
    for tok in pipe.llm.stream(
        __import__("job_scout.rag.generate", fromlist=["SYSTEM_PROMPT"]).SYSTEM_PROMPT,
        __import__("job_scout.rag.generate", fromlist=["build_user_prompt"]).build_user_prompt(
            q, "（测试用岗位片段）", profile_text=pt
        ),
    ):
        if first is None:
            first = time.time() - t0
        if time.time() - t0 > 8:
            break
    print(f"  {label}: 首 token {first:.1f}s")
