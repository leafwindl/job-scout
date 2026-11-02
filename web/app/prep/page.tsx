"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Ban,
  Check,
  Lightbulb,
  Loader2,
  RefreshCw,
  Sparkles,
  TrendingUp,
} from "lucide-react";

import PageHeader from "@/components/PageHeader";
import { EmptyState, ProgressBar, SectionHeader, Stat } from "@/components/ui";
import { api, type PrepResult } from "@/lib/api";

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="flex items-center gap-2 text-xs text-fg3">
          <Loader2 size={13} className="animate-spin text-accent" />
          正在把在架岗位和你简历做差集，约 20 秒…
        </div>
        <div className="mt-4 space-y-2.5">
          <div className="skel h-3.5 w-4/5" />
          <div className="skel h-3.5 w-3/5" />
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card space-y-3 p-5">
              <div className="skel h-4 w-1/3" />
              <div className="skel h-3 w-full" />
              <div className="skel h-3 w-4/5" />
              <div className="skel h-14 w-full" />
            </div>
          ))}
        </div>
        <div className="card space-y-3 p-5">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="skel h-3 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function PrepPage() {
  const [data, setData] = useState<PrepResult | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setErr("");
    api
      .prep()
      .then(setData)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const learnCount = data?.learn?.length ?? 0;
  const haveCount = data?.have?.length ?? 0;
  const missingCount = data?.missing?.length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Prepare"
        title="技术准备"
        description="把在架岗位的要求和你的简历做差集，按「性价比」排序：先补什么、哪些已经会只是没讲清楚、什么不值得花时间。"
        actions={
          data ? (
            <button className="btn btn-ghost" onClick={load} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> 分析中
                </>
              ) : (
                <>
                  <RefreshCw size={14} /> 重新分析
                </>
              )}
            </button>
          ) : undefined
        }
      />

      {loading && !data && <LoadingSkeleton />}

      {err && !loading && (
        <div className="card p-5">
          {err.includes("400") ? (
            <>
              <div className="text-[13px] font-medium text-fg">还没有上传简历</div>
              <p className="mt-1 text-xs leading-[1.7] text-fg3">
                技术准备需要拿你的技能和在架岗位做差集。先上传 PDF 简历，再回来分析。
              </p>
              <Link href="/profile" className="btn btn-primary btn-sm mt-4">
                去上传简历
              </Link>
            </>
          ) : (
            <>
              <div className="text-[13px] font-medium text-fg">分析失败</div>
              <p className="mt-1 text-xs text-fg3">{err}</p>
              <button className="btn btn-ghost btn-sm mt-4" onClick={load}>
                <RefreshCw size={13} /> 重试
              </button>
            </>
          )}
        </div>
      )}

      {!loading && !err && data && (
        <>
          {/* 结论 */}
          <section className="animate-rise card overflow-hidden">
            <div className="flex items-start gap-3 px-5 py-5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-accent/25 bg-accent/10 text-accent">
                <Lightbulb size={15} strokeWidth={1.9} />
              </span>
              <div className="min-w-0">
                <div className="eyebrow">概览结论</div>
                <p className="mt-2 max-w-3xl text-[14px] leading-[1.8] text-fg">
                  {data.overview || "根据当前在架岗位与你的简历，以下是优先级最高的准备方向。"}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className="tag">范围：{data.scope}</span>
                  <span className="tag">{haveCount} 项已具备</span>
                  <span className="tag tag-amber">{missingCount} 项缺口</span>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-px border-t border-line/60 bg-line/50">
              <div className="bg-panel px-5 py-3.5">
                <Stat label="已具备技能" value={haveCount} unit="项" tone="mint" />
              </div>
              <div className="bg-panel px-5 py-3.5">
                <Stat label="岗位缺口" value={missingCount} unit="项" tone="amber" />
              </div>
              <div className="bg-panel px-5 py-3.5">
                <Stat label="建议优先补" value={learnCount} unit="个方向" tone="accent" />
              </div>
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
            {/* 优先补 */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <SectionHeader
                  title="建议优先补"
                  hint={learnCount > 0 ? `${learnCount} 个方向` : undefined}
                  icon={Sparkles}
                />
              </div>

              {data.learn && data.learn.length > 0 ? (
                data.learn.map((item, i) => {
                  const demand = data.demand.find((d) => d.skill === item.skill);
                  return (
                    <article key={i} className="card p-5">
                      <div className="flex items-start gap-3">
                        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-accent/25 bg-accent/10 text-3xs font-semibold tabular-nums text-accent">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-[14px] font-medium text-fg">{item.skill}</h3>
                            {demand && (
                              <span className="tag tag-accent">{demand.jobs} 个岗位要求</span>
                            )}
                          </div>
                          {item.why && (
                            <p className="mt-1.5 text-[13px] leading-[1.7] text-fg2">
                              {item.why}
                            </p>
                          )}
                        </div>
                      </div>
                      {item.how && (
                        <div className="mt-3 rounded-lg border border-line/60 bg-panel2/40 px-3 py-2.5">
                          <div className="text-2xs font-medium text-mint">怎么学</div>
                          <p className="mt-1 text-xs leading-[1.75] text-fg2">{item.how}</p>
                        </div>
                      )}
                    </article>
                  );
                })
              ) : (
                <div className="card">
                  <EmptyState
                    icon={Sparkles}
                    title="暂时没有需要优先补的方向"
                    description="你简历里的技能已经覆盖了在架岗位的常见要求。"
                    compact
                  />
                </div>
              )}
            </section>

            {/* 高频要求 */}
            <aside className="card p-5 lg:sticky lg:top-6">
              <SectionHeader
                title="高频要求"
                hint="按岗位命中数排序"
                icon={TrendingUp}
              />
              <div className="mt-4 space-y-2.5">
                {data.demand.slice(0, 14).map((d) => {
                  const mine = data.have.includes(d.skill);
                  return (
                    <div key={d.skill}>
                      <div className="flex items-center gap-2">
                        <span
                          className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                            mine ? "bg-mint" : "bg-fg3/50"
                          }`}
                        />
                        <span
                          className={`min-w-0 flex-1 truncate text-xs ${
                            mine ? "text-fg" : "text-fg2"
                          }`}
                        >
                          {d.skill}
                        </span>
                        {mine && <Check size={10} className="shrink-0 text-mint" />}
                        <span className="shrink-0 text-3xs tabular-nums text-fg3">
                          {d.jobs} 岗
                        </span>
                      </div>
                      <div className="mt-1 pl-3.5">
                        <ProgressBar
                          value={d.ratio * 100}
                          tone={mine ? "mint" : "default"}
                          height="h-1"
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="mt-4 flex items-center gap-3 border-t border-line/60 pt-3 text-3xs text-fg3">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-mint" /> 你简历里有
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-fg3/50" /> 待补
                </span>
              </div>
            </aside>
          </div>

          {/* 放大 / 跳过 */}
          <div className="grid gap-4 md:grid-cols-2">
            {data.leverage && data.leverage.length > 0 && (
              <section className="card p-5">
                <SectionHeader
                  title="已经会，但没讲清楚的"
                  hint="放大就有分"
                  icon={Sparkles}
                />
                <ul className="mt-3 space-y-2.5">
                  {data.leverage.map((x, i) => (
                    <li key={i} className="flex gap-2.5">
                      <span className="mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-mint/30 bg-mint/10 text-[9px] text-mint">
                        +
                      </span>
                      <span className="text-[13px] leading-[1.7] text-fg2">{x}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {data.skip && data.skip.length > 0 && (
              <section className="card p-5">
                <SectionHeader
                  title="不值得花时间的"
                  hint="先别学"
                  icon={Ban}
                />
                <ul className="mt-3 space-y-2.5">
                  {data.skip.map((x, i) => (
                    <li key={i} className="flex gap-2.5">
                      <span className="mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-rose-500/30 bg-rose-500/10 text-[9px] text-rose-300">
                        −
                      </span>
                      <span className="text-[13px] leading-[1.7] text-fg3">{x}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </>
      )}
    </div>
  );
}
