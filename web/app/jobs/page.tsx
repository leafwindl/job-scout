"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Loader2,
  RotateCcw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";

import JobRow, { JobRowSkeleton } from "@/components/JobRow";
import PageHeader from "@/components/PageHeader";
import { EmptyState } from "@/components/ui";
import { api, type JobItem } from "@/lib/api";

const CATEGORIES = [
  { value: "", label: "全部方向" },
  { value: "Agent 编排", label: "Agent 编排" },
  { value: "RAG/知识库", label: "RAG / 知识库" },
  { value: "全栈/前端", label: "全栈 / 前端" },
  { value: "后端/平台", label: "后端 / 平台" },
  { value: "算法/模型", label: "算法 / 模型" },
  { value: "通用/后端底子", label: "通用" },
];

const PAGE_SIZE = 20;

function pageWindow(page: number, pages: number): number[] {
  const start = Math.max(1, Math.min(page - 2, pages - 4));
  const end = Math.min(pages, start + 4);
  const out: number[] = [];
  for (let i = start; i <= end; i += 1) out.push(i);
  return out;
}

export default function JobsPage() {
  const [keyword, setKeyword] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(keyword), 300);
    return () => clearTimeout(t);
  }, [keyword]);

  useEffect(() => {
    setPage(1);
  }, [debounced, category]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr("");
    api
      .jobs({ keyword: debounced, category, page, size: PAGE_SIZE })
      .then((r) => {
        if (!alive) return;
        setTotal(r.total);
        setItems(r.items);
      })
      .catch(() => {
        if (!alive) return;
        setErr("岗位数据加载失败，确认后端服务在运行。");
        setTotal(0);
        setItems([]);
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [debounced, category, page, tick]);

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered = Boolean(debounced || category);
  const activeLabel =
    CATEGORIES.find((c) => c.value === category)?.label ?? "全部方向";

  function reset() {
    setKeyword("");
    setCategory("");
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Jobs"
        title="岗位库"
        description="按方向筛选在架实习岗位，点进去看匹配度、缺口和招呼语。"
        actions={
          <Link href="/ask" className="btn btn-ghost">
            用自然语言问岗位 <ArrowRight size={15} />
          </Link>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[212px_minmax(0,1fr)]">
        {/* 筛选栏 */}
        <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <div className="card p-2.5">
            <div className="relative">
              <Search
                size={14}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg3"
              />
              <input
                className="input pl-8 pr-8"
                placeholder="搜索岗位 / 公司 / 技能"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                aria-label="搜索岗位"
              />
              {keyword && (
                <button
                  type="button"
                  onClick={() => setKeyword("")}
                  className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-fg3 hover:bg-panel3 hover:text-fg"
                  aria-label="清空搜索"
                >
                  <X size={12} />
                </button>
              )}
            </div>

            <div className="mt-3 hidden lg:block">
              <div className="flex items-center gap-1.5 px-2 pb-1">
                <SlidersHorizontal size={11} className="text-fg3" />
                <span className="eyebrow text-3xs">方向</span>
              </div>
              <div className="space-y-0.5">
                {CATEGORIES.map((c) => {
                  const active = category === c.value;
                  return (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => setCategory(c.value)}
                      aria-pressed={active}
                      className={`flex h-8 w-full items-center justify-between rounded-md px-2 text-left text-[13px] transition-colors ${
                        active
                          ? "bg-accent/10 font-medium text-accent"
                          : "text-fg2 hover:bg-panel2/70 hover:text-fg"
                      }`}
                    >
                      {c.label}
                      {active && <span className="h-1 w-1 rounded-full bg-accent" />}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="card hidden p-4 lg:block">
            <div className="stat-label">当前筛选</div>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-[20px] font-semibold tabular-nums text-fg">{total}</span>
              <span className="text-2xs text-fg3">个岗位</span>
            </div>
            <p className="mt-1.5 text-2xs leading-4 text-fg3">
              {activeLabel}
              {debounced ? ` · 关键词「${debounced}」` : ""}
            </p>
          </div>
        </aside>

        {/* 岗位列表 */}
        <div className="min-w-0 space-y-4">
          {/* 移动端方向筛选 */}
          <div className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-0.5 no-scrollbar sm:mx-0 sm:px-0 lg:hidden">
            {CATEGORIES.map((c) => {
              const active = category === c.value;
              return (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setCategory(c.value)}
                  aria-pressed={active}
                  className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                    active
                      ? "border-accent/40 bg-accent/10 text-accent"
                      : "border-line bg-panel text-fg2"
                  }`}
                >
                  {c.label}
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs text-fg3">
              共 <span className="tabular-nums text-fg">{total}</span> 条
              {filtered && (
                <button
                  type="button"
                  onClick={reset}
                  className="ml-2 inline-flex items-center gap-1 text-fg3 transition-colors hover:text-accent"
                >
                  <RotateCcw size={11} /> 重置筛选
                </button>
              )}
            </div>
            <div className="flex items-center gap-2 text-2xs text-fg3">
              {loading && (
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 size={12} className="animate-spin" /> 加载中
                </span>
              )}
              <span className="tabular-nums">
                第 {page} / {pages} 页
              </span>
            </div>
          </div>

          {err && (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/30 bg-rose-500/[0.06] px-4 py-3 text-[13px] text-rose-300">
              <span>{err}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setTick((t) => t + 1)}>
                重试
              </button>
            </div>
          )}

          <div className="card overflow-hidden">
            {loading ? (
              <div className="divide-y divide-line/60">
                {Array.from({ length: 6 }).map((_, i) => (
                  <JobRowSkeleton key={i} />
                ))}
              </div>
            ) : items.length > 0 ? (
              <div className="divide-y divide-line/60">
                {items.map((job) => (
                  <JobRow key={job.job_id} job={job} />
                ))}
              </div>
            ) : (
              !err && (
                <EmptyState
                  icon={Search}
                  title="没有匹配的岗位"
                  description="换个关键词，或者清空方向筛选再看看。"
                >
                  <button className="btn btn-ghost btn-sm" onClick={reset}>
                    <RotateCcw size={13} /> 重置筛选
                  </button>
                </EmptyState>
              )
            )}
          </div>

          {pages > 1 && (
            <nav
              className="flex items-center justify-between gap-3"
              aria-label="分页"
            >
              <button
                className="btn btn-ghost btn-sm"
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft size={14} /> 上一页
              </button>

              <div className="hidden items-center gap-1 sm:flex">
                {pageWindow(page, pages).map((n) => (
                  <button
                    key={n}
                    onClick={() => setPage(n)}
                    aria-current={n === page ? "page" : undefined}
                    className={`flex h-8 w-8 items-center justify-center rounded-md text-xs tabular-nums transition-colors ${
                      n === page
                        ? "bg-accent/15 font-medium text-accent"
                        : "text-fg3 hover:bg-panel2 hover:text-fg"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>

              <button
                className="btn btn-ghost btn-sm"
                disabled={page >= pages || loading}
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
              >
                下一页 <ChevronRight size={14} />
              </button>
            </nav>
          )}
        </div>
      </div>
    </div>
  );
}
