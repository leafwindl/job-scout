const ROWS = [
  { name: "BM25", r1: 0.168, r5: 0.521, r10: 0.578, p10: 0.609, mrr: 0.864, highlight: false },
  { name: "向量（bge-small-zh）", r1: 0.106, r5: 0.297, r10: 0.367, p10: 0.43, mrr: 0.76, highlight: false },
  { name: "RRF 融合", r1: 0.146, r5: 0.448, r10: 0.533, p10: 0.645, mrr: 0.962, highlight: true },
];

const TYPES = [
  { kind: "技能", n: 12, r10: 0.152, p10: 1.0, mrr: 1.0 },
  { kind: "公司", n: 12, r10: 0.853, p10: 0.375, mrr: 0.958 },
  { kind: "区域", n: 9, r10: 0.615, p10: 0.533, mrr: 0.917 },
];

const fmt = (v: number) => v.toFixed(3);

export default function EvalPage() {
  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-semibold">检索评测</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          评测集 33 条，由规则合成（不依赖人工标注）：技能 / 公司 / 区域三类查询。
          所有指标可用 <code className="rounded bg-panel2 px-1">job-scout rag-eval</code> 复现。
        </p>
      </section>

      <section className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs text-slate-500">
              <th className="px-4 py-3 font-normal">配置</th>
              <th className="px-4 py-3 text-right font-normal">Recall@1</th>
              <th className="px-4 py-3 text-right font-normal">Recall@5</th>
              <th className="px-4 py-3 text-right font-normal">Recall@10</th>
              <th className="px-4 py-3 text-right font-normal">Precision@10</th>
              <th className="px-4 py-3 text-right font-normal">MRR</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr
                key={r.name}
                className={`border-b border-line/60 last:border-0 ${
                  r.highlight ? "bg-accent/5" : ""
                }`}
              >
                <td className="px-4 py-3">{r.name}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmt(r.r1)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmt(r.r5)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmt(r.r10)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmt(r.p10)}</td>
                <td
                  className={`px-4 py-3 text-right tabular-nums ${
                    r.highlight ? "text-mint" : ""
                  }`}
                >
                  {fmt(r.mrr)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="card p-5">
          <div className="text-xs text-slate-500">MRR 提升</div>
          <div className="mt-1 text-2xl font-semibold text-mint">+11.3%</div>
          <div className="mt-1 text-xs text-slate-500">0.864 → 0.962（验收标准 ≥5%）</div>
        </div>
        <div className="card p-5">
          <div className="text-xs text-slate-500">技能类 Precision@10</div>
          <div className="mt-1 text-2xl font-semibold">1.000</div>
          <div className="mt-1 text-xs text-slate-500">返回 10 条全部相关</div>
        </div>
        <div className="card p-5">
          <div className="text-xs text-slate-500">检索 P95</div>
          <div className="mt-1 text-2xl font-semibold">30 ms</div>
          <div className="mt-1 text-xs text-slate-500">验收标准 &lt; 3s</div>
        </div>
      </section>

      <section className="card overflow-hidden">
        <div className="border-b border-line px-4 py-3 text-sm text-slate-300">
          按查询类型（融合配置）
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs text-slate-500">
              <th className="px-4 py-3 font-normal">类型</th>
              <th className="px-4 py-3 text-right font-normal">数量</th>
              <th className="px-4 py-3 text-right font-normal">Recall@10</th>
              <th className="px-4 py-3 text-right font-normal">Precision@10</th>
              <th className="px-4 py-3 text-right font-normal">MRR</th>
            </tr>
          </thead>
          <tbody>
            {TYPES.map((t) => (
              <tr key={t.kind} className="border-b border-line/60 last:border-0">
                <td className="px-4 py-3">{t.kind}</td>
                <td className="px-4 py-3 text-right tabular-nums">{t.n}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmt(t.r10)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmt(t.p10)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{fmt(t.mrr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card p-5 text-sm text-slate-400">
        <div className="mb-2 text-slate-300">为什么技能类 Recall 低、Precision 高</div>
        <p>
          「哪些岗位要求 Python」有 118 个正确答案，返回 10 条时 Recall 上限只有 0.085；
          但返回的 10 条全部相关，Precision 才是这个场景该看的指标。
          公司/区域类答案少，用 Recall 和 MRR 更合适。
        </p>
      </section>
    </div>
  );
}
