"""检索评测：合成评测集 + Recall@K / MRR。

评测集是**规则合成**的，不靠人工标注：
- 技能类：「哪些岗位要求 LangGraph」→ gold = 正文提到该词的岗位
- 公司类：「安点科技在招什么」    → gold = 该公司的岗位
- 区域类：「海珠区的实习岗」      → gold = 该区且标题含实习的岗位

好处：可复现、可扩展、改了检索策略能立刻重跑对比。
限制：答案数量受控在 [2, 15]，避免 Recall@10 被大量 gold 稀释。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from job_scout.rag.corpus import Doc


@dataclass
class EvalItem:
    query: str
    gold: set[str]  # 全量正确答案，不采样
    kind: str


def _add(items: list[EvalItem], seen: set[str], query: str, gold: set[str], kind: str) -> None:
    if query in seen or len(gold) < 2:
        return
    seen.add(query)
    items.append(EvalItem(query=query, gold=gold, kind=kind))


def build_eval_set(docs: list[Doc], per_kind: int = 12) -> list[EvalItem]:
    items: list[EvalItem] = []
    seen: set[str] = set()

    # 1) 技能类：用 doc.meta["terms"]（已从正文抽取）
    by_term: dict[str, set[str]] = defaultdict(set)
    for d in docs:
        for t in d.meta.get("terms", []):
            by_term[t].add(d.doc_id)
    for term, ids in sorted(by_term.items(), key=lambda x: -len(x[1]))[: per_kind * 3]:
        _add(items, seen, f"哪些岗位要求 {term}", ids, "技能")
        if sum(1 for i in items if i.kind == "技能") >= per_kind:
            break

    # 2) 公司类
    by_company: dict[str, set[str]] = defaultdict(set)
    for d in docs:
        if d.company:
            by_company[d.company].add(d.doc_id)
    for company, ids in sorted(by_company.items(), key=lambda x: -len(x[1])):
        _add(items, seen, f"{company} 在招什么岗位", ids, "公司")
        if sum(1 for i in items if i.kind == "公司") >= per_kind:
            break

    # 3) 区域类（限定实习）
    by_district: dict[str, set[str]] = defaultdict(set)
    for d in docs:
        if d.meta.get("is_intern") and d.meta.get("district"):
            by_district[d.meta["district"]].add(d.doc_id)
    for district, ids in sorted(by_district.items(), key=lambda x: -len(x[1]))[: per_kind]:
        _add(items, seen, f"{district}的实习岗位", ids, "区域")

    return items


def recall_at_k(ranked: list[str], gold: set[str], k: int) -> float:
    if not gold:
        return 0.0
    return len(set(ranked[:k]) & gold) / len(gold)


def precision_at_k(ranked: list[str], gold: set[str], k: int) -> float:
    """Top-K 里有多少条是相关的。

    对「答案很多」的查询（如「哪些岗位要求 Python」）比 Recall 更合理：
    Recall 的分母可能有上百条，上限被稀释；Precision 只看你返回的这批准不准。
    """
    top = ranked[:k]
    if not top:
        return 0.0
    return sum(1 for d in top if d in gold) / len(top)


def mrr(ranked: list[str], gold: set[str]) -> float:
    for i, doc_id in enumerate(ranked, 1):
        if doc_id in gold:
            return 1.0 / i
    return 0.0


def evaluate(retriever, items: list[EvalItem], ks=(1, 5, 10)) -> dict:
    max_k = max(ks)
    rows = []
    for it in items:
        hits = retriever.search(it.query, k=max_k)
        ranked = [d.doc_id for d, _ in hits]
        rows.append(
            {
                "query": it.query,
                "kind": it.kind,
                "gold": len(it.gold),
                "recall": {k: recall_at_k(ranked, it.gold, k) for k in ks},
                "precision": {k: precision_at_k(ranked, it.gold, k) for k in ks},
                "mrr": mrr(ranked, it.gold),
            }
        )

    def avg_recall(subset: list[dict], k: int) -> float:
        return sum(r["recall"][k] for r in subset) / len(subset) if subset else 0.0

    def avg_prec(subset: list[dict], k: int) -> float:
        return sum(r["precision"][k] for r in subset) / len(subset) if subset else 0.0

    overall = {
        "n": len(rows),
        f"recall@{ks[0]}": avg_recall(rows, ks[0]),
        f"recall@{ks[1]}": avg_recall(rows, ks[1]),
        f"recall@{max_k}": avg_recall(rows, max_k),
        f"precision@{max_k}": avg_prec(rows, max_k),
        "mrr": sum(r["mrr"] for r in rows) / len(rows) if rows else 0.0,
    }

    by_kind = {}
    for kind in {r["kind"] for r in rows}:
        sub = [r for r in rows if r["kind"] == kind]
        by_kind[kind] = {
            "n": len(sub),
            f"recall@{max_k}": avg_recall(sub, max_k),
            f"precision@{max_k}": avg_prec(sub, max_k),
            "mrr": sum(r["mrr"] for r in sub) / len(sub),
        }

    return {"overall": overall, "by_kind": by_kind, "rows": rows}
