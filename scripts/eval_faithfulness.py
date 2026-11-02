"""M2 验收：忠实度评测。

做法：
1. 用规则合成的评测问题跑完整问答（检索 + 生成）
2. 用另一个 LLM 调用做 judge：判断回答里的事实是否都能被片段支持
3. 统计忠实度、引用有效率、拒答率

成本约每条 2 次调用，30 条约几分钱。
"""

from __future__ import annotations

import json
import re
import sys

from job_scout.rag.evaluate import build_eval_set
from job_scout.rag.pipeline import get_pipeline

N = int(sys.argv[1]) if len(sys.argv) > 1 else 12

JUDGE_PROMPT = """你是严格的评审员。给定一段【回答】和它依据的【片段】，
判断回答中的事实性陈述是否都能被片段直接支持。

只输出 JSON，不要其它内容：
{"faithful": true 或 false, "unsupported": ["片段不支持的说法"], "reason": "一句话理由"}

注意：
- 回答里如果只是「没有找到」，算 faithful=true
- 引用的岗位名、公司名、薪资必须能在片段里找到
- 回答做了合理归纳（比如「多数岗位要求 Python」）算 faithful
"""


def judge(llm, answer: str, context: str) -> dict:
    # 注意：这里不能截断 context，否则 judge 看不到后几条片段，
    # 会把「引用片段外的内容」误判成幻觉（踩过）
    user = f"【片段】\n{context}\n\n【回答】\n{answer}\n"
    raw = llm.complete(JUDGE_PROMPT, user, temperature=0.0)

    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {"faithful": None, "unsupported": [], "reason": f"judge 输出无法解析: {raw[:80]}"}
    try:
        return json.loads(m.group())
    except Exception:
        return {"faithful": None, "unsupported": [], "reason": "json 解析失败"}


def main() -> None:
    pipe = get_pipeline()
    if not pipe.has_llm:
        print("没有 LLM，无法评测")
        return

    items = build_eval_set(pipe.docs, per_kind=max(2, N // 3))[:N]
    print(f"评测问题数: {len(items)}\n")

    rows = []
    for i, it in enumerate(items, 1):
        ans = pipe.ask(it.query, k=5)
        if ans.mode == "refused":
            rows.append({"q": it.query, "mode": ans.mode, "faithful": True, "cites": 0})
            print(f"[{i}/{len(items)}] {it.query[:30]} → 拒答")
            continue

        verdict = judge(pipe.llm, ans.text, ans.context)
        rows.append(
            {
                "q": it.query,
                "mode": ans.mode,
                "faithful": verdict.get("faithful"),
                "reason": verdict.get("reason", ""),
                "unsupported": verdict.get("unsupported", []),
                "cites": len(ans.citations),
            }
        )
        mark = "✓" if verdict.get("faithful") else "✗"
        print(
            f"[{i}/{len(items)}] {it.query[:30]:<32} {mark} "
            f"引用={len(ans.citations)} {verdict.get('reason','')[:40]}"
        )

    judged = [r for r in rows if r["faithful"] is not None]
    ok = sum(1 for r in judged if r["faithful"])
    with_cite = sum(1 for r in rows if r["cites"] > 0)

    print("\n" + "=" * 50)
    print(f"有效评测: {len(judged)}/{len(rows)}")
    print(f"忠实回答: {ok}/{len(judged)} = {ok / len(judged) * 100:.1f}%" if judged else "无有效结果")
    print(f"带引用的回答: {with_cite}/{len(rows)}")
    print(f"验收标准 忠实度 ≥85%: {'通过' if judged and ok / len(judged) >= 0.85 else '未通过'}")

    bad = [r for r in judged if not r["faithful"]]
    if bad:
        print("\n不忠实样例:")
        for r in bad[:5]:
            print(f"  Q: {r['q']}")
            print(f"     {r.get('reason','')[:80]}")
            for u in (r.get("unsupported") or [])[:2]:
                print(f"     不支持: {u[:80]}")


if __name__ == "__main__":
    main()
