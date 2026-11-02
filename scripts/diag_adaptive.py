"""诊断自适应路由的判据：看两路 top1 一致率与分差分布。"""

from __future__ import annotations

from job_scout.rag.bm25 import BM25Retriever
from job_scout.rag.corpus import load_docs
from job_scout.rag.embedder import Embedder
from job_scout.rag.evaluate import build_eval_set
from job_scout.rag.hybrid import rrf_fuse
from job_scout.rag.vector import VectorRetriever

docs = load_docs("data/job_scout.db", only_intern=True)
items = build_eval_set(docs, per_kind=12)

bm25 = BM25Retriever(docs, field="text")
emb = Embedder()
vec = VectorRetriever.build(docs, emb)

same = 0
gaps = []
for it in items:
    bm = bm25.search(it.query, k=50)
    vs = vec.search(it.query, k=50)
    if bm and vs and bm[0][0].doc_id == vs[0][0].doc_id:
        same += 1

    fused = rrf_fuse([bm, vs])
    if len(fused) >= 2:
        c1, c2 = fused[0][1], fused[1][1]
        gaps.append((c1 - c2) / c1 if c1 > 0 else 0.0)

gaps.sort()
n = len(gaps)
print(f"查询数: {len(items)}")
print(f"两路 top1 一致: {same}/{len(items)} ({same / len(items) * 100:.0f}%)")
print("\nRRF 相对分差分布:")
print(f"  min   {gaps[0]:.4f}")
print(f"  p25   {gaps[n // 4]:.4f}")
print(f"  median{gaps[n // 2]:.4f}")
print(f"  p75   {gaps[3 * n // 4]:.4f}")
print(f"  max   {gaps[-1]:.4f}")
for th in (0.02, 0.05, 0.1, 0.15, 0.3):
    skip = sum(1 for g in gaps if g > th)
    print(f"  阈值 {th:<5} → 跳过 {skip}/{n} ({skip / n * 100:.0f}%)")
