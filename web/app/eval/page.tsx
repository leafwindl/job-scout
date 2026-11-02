import Link from "next/link";
import { ArrowUpRight, FlaskConical } from "lucide-react";

import PageHeader from "@/components/PageHeader";
import { SectionHeader, Stat } from "@/components/ui";

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

function TableShell({ children }: { children: React.ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

export default function EvalPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Eval"
        title="检索评测"
        description="评测集 33 条，由规则合成（不依赖人工标注）：技能、公司、区域三类查询。所有指标可用 job-scout rag-eval 复现。"
        actions={
          <Link href="/ask" className="btn btn-ghost">
            去问答验证 <ArrowUpRight size={14} />
          </Link>
        }
      />

      <section className="animate-rise card overflow-hidden">
        <div className="grid grid-cols-2 gap-px bg-line/50 sm:grid-cols-4">
          <div className="bg-panel px-5 py-4">
            <Stat
              label="MRR 提升"
              value="+11.3%"
              tone="mint"
              hint="0.864 → 0.962（验收 ≥ 5%）"
            />
          </div>
          <div className="bg-panel px-5 py-4">
            <Stat
              label="技能类 P@10"
              value="1.000"
              hint="返回的 10 条全部相关"
            />
          </div>
          <div className="bg-panel px-5 py-4">
            <Stat label="检索 P95" value="30" unit="ms" hint="验收标准 < 3s" />
          </div>
          <div className="bg-panel px-5 py-4">
            <Stat label="评测集" value="33" unit="条" hint="技能 / 公司 / 区域" />
          </div>
        </div>
      </section>

      <section className="card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line/60 px-5 py-3.5">
          <SectionHeader
            title="整体指标"
            hint="三类查询合并"
            icon={FlaskConical}
          />
          <span className="text-2xs text-fg3">RRF（Reciprocal Rank Fusion）为默认配置</span>
        </div>
        <TableShell>
          <table className="w-full min-w-[680px] text-[13px]">
            <thead>
              <tr className="border-b border-line/60 text-left text-2xs text-fg3">
                <th className="px-5 py-3 font-normal">配置</th>
                <th className="px-4 py-3 text-right font-normal">Recall@1</th>
                <th className="px-4 py-3 text-right font-normal">Recall@5</th>
                <th className="px-4 py-3 text-right font-normal">Recall@10</th>
                <th className="px-4 py-3 text-right font-normal">Precision@10</th>
                <th className="px-5 py-3 text-right font-normal">MRR</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((r) => (
                <tr
                  key={r.name}
                  className={`border-b border-line/40 last:border-0 ${
                    r.highlight ? "bg-accent/[0.06]" : "hover:bg-panel2/30"
                  }`}
                >
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <span className={r.highlight ? "text-fg" : "text-fg2"}>{r.name}</span>
                      {r.highlight && <span className="tag tag-accent">默认</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-right tabular-nums text-fg2">{fmt(r.r1)}</td>
                  <td className="px-4 py-3.5 text-right tabular-nums text-fg2">{fmt(r.r5)}</td>
                  <td className="px-4 py-3.5 text-right tabular-nums text-fg2">{fmt(r.r10)}</td>
                  <td className="px-4 py-3.5 text-right tabular-nums text-fg2">{fmt(r.p10)}</td>
                  <td
                    className={`px-5 py-3.5 text-right tabular-nums ${
                      r.highlight ? "font-medium text-mint" : "text-fg2"
                    }`}
                  >
                    {fmt(r.mrr)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      </section>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
        <section className="card overflow-hidden">
          <div className="border-b border-line/60 px-5 py-3.5">
            <SectionHeader title="按查询类型" hint="融合配置" />
          </div>
          <TableShell>
            <table className="w-full min-w-[480px] text-[13px]">
              <thead>
                <tr className="border-b border-line/60 text-left text-2xs text-fg3">
                  <th className="px-5 py-3 font-normal">类型</th>
                  <th className="px-4 py-3 text-right font-normal">数量</th>
                  <th className="px-4 py-3 text-right font-normal">Recall@10</th>
                  <th className="px-4 py-3 text-right font-normal">Precision@10</th>
                  <th className="px-5 py-3 text-right font-normal">MRR</th>
                </tr>
              </thead>
              <tbody>
                {TYPES.map((t) => (
                  <tr
                    key={t.kind}
                    className="border-b border-line/40 last:border-0 hover:bg-panel2/30"
                  >
                    <td className="px-5 py-3.5 text-fg2">{t.kind}</td>
                    <td className="px-4 py-3.5 text-right tabular-nums text-fg3">{t.n}</td>
                    <td className="px-4 py-3.5 text-right tabular-nums text-fg2">{fmt(t.r10)}</td>
                    <td className="px-4 py-3.5 text-right tabular-nums text-fg2">{fmt(t.p10)}</td>
                    <td className="px-5 py-3.5 text-right tabular-nums text-fg2">{fmt(t.mrr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        </section>

        <aside className="card p-5">
          <SectionHeader title="为什么技能类 Recall 低、Precision 高" />
          <p className="mt-3 text-[13px] leading-[1.8] text-fg2">
            「哪些岗位要求 Python」有 118 个正确答案，返回 10 条时 Recall 上限只有 0.085；
            但返回的 10 条全部相关，Precision 才是这个场景该看的指标。
          </p>
          <p className="mt-2.5 text-[13px] leading-[1.8] text-fg2">
            公司 / 区域类答案少，用 Recall 和 MRR 更合适。所以融合配置的收益主要看 MRR 和
            Precision@10。
          </p>
          <div className="mt-4 border-t border-line/60 pt-3 text-2xs text-fg3">
            评测集由规则从岗位字段合成，存在标注噪声；指标用于横向比较配置，不代表线上效果。
          </div>
        </aside>
      </div>
    </div>
  );
}
