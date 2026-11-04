"""调试最长公共子串匹配。"""

from __future__ import annotations

import difflib

target = "AI 求职助手"
names = [
    "Echo AI 助手 App —— Agent 工具调度与长期记忆",
    "智能测试全流程平台 —— 多智能体编排与 RAG 检索",
    "完全不相干的名字",
]

print(f"target = {target!r} (len={len(target)})\n")
for name in names:
    sm = difflib.SequenceMatcher(None, target, name)
    m = sm.find_longest_match(0, len(target), 0, len(name))
    size = m.size
    score = size / max(1, min(len(target), len(name)))
    print(f"{name[:30]!r}")
    print(f"  最长公共子串: {target[m.a : m.a + m.size]!r}  size={size}  score={score:.2f}")
