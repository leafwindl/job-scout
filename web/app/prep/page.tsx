"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type PrepResult } from "@/lib/api";

export default function PrepPage() {
  const [data, setData] = useState<PrepResult | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .prep()
      .then(setData)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">技术准备</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          把在架岗位的要求和你简历里的技能做差集，按「性价比」排序告诉你先补什么。
        </p>
      </div>

      {loading && <div className="card p-6 text-sm text-slate-400">分析中（约 20 秒）…</div>}

      {err && (
        <div className="card border-amber-600/40 p-5 text-sm text-amber-400">
          {err.includes("400") ? (
            <>
              还没上传简历。先去{" "}
              <Link href="/profile" className="text-accent underline">
                我的简历
              </Link>{" "}
              页上传 PDF。
            </>
          ) : (
            err
          )}
        </div>
      )}

      {data && (
        <>
          {data.overview && (
            <div className="card border-accent/30 p-5 text-sm leading-relaxed text-slate-200">
              {data.overview}
            </div>
          )}

          {data.learn && data.learn.length > 0 && (
            <section className="card p-6">
              <h2 className="mb-4 text-sm font-medium text-slate-300">建议优先补</h2>
              <div className="space-y-4">
                {data.learn.map((x, i) => (
                  <div key={i} className="rounded-lg border border-line p-4">
                    <div className="text-sm text-slate-100">{x.skill}</div>
                    {x.why && <div className="mt-1 text-xs text-slate-400">{x.why}</div>}
                    {x.how && (
                      <div className="mt-2 rounded bg-panel2 p-2.5 text-xs leading-relaxed text-slate-300">
                        <span className="text-mint">怎么学：</span>
                        {x.how}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {data.leverage && data.leverage.length > 0 && (
            <section className="card p-6">
              <h2 className="mb-3 text-sm font-medium text-mint">
                已经会、但没讲清楚的（放大就有分）
              </h2>
              <ul className="space-y-2 text-sm text-slate-300">
                {data.leverage.map((x, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-mint">+</span>
                    <span>{x}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.skip && data.skip.length > 0 && (
            <section className="card p-6">
              <h2 className="mb-3 text-sm font-medium text-rose-400">不值得花时间的</h2>
              <ul className="space-y-2 text-sm text-slate-400">
                {data.skip.map((x, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-rose-400">−</span>
                    <span>{x}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="card p-6">
            <h2 className="mb-3 text-sm font-medium text-slate-300">
              高频要求 <span className="text-slate-500">（{data.scope}）</span>
            </h2>
            <div className="space-y-1.5">
              {data.demand.slice(0, 14).map((d) => {
                const mine = data.have.includes(d.skill);
                return (
                  <div key={d.skill} className="flex items-center gap-3 text-sm">
                    <span className={`w-6 text-center ${mine ? "text-mint" : "text-slate-600"}`}>
                      {mine ? "✓" : "·"}
                    </span>
                    <span className={`w-40 truncate ${mine ? "text-slate-200" : "text-slate-400"}`}>
                      {d.skill}
                    </span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel2">
                      <div
                        className={`h-full rounded-full ${mine ? "bg-mint" : "bg-slate-600"}`}
                        style={{ width: `${Math.round(d.ratio * 100)}%` }}
                      />
                    </div>
                    <span className="w-14 text-right text-xs tabular-nums text-slate-500">
                      {d.jobs} 岗
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 text-xs text-slate-600">✓ = 你简历里有</div>
          </section>
        </>
      )}
    </div>
  );
}
