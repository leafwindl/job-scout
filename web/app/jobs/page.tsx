"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type JobItem } from "@/lib/api";

const CATEGORIES = [
  { value: "", label: "全部方向" },
  { value: "Agent 编排", label: "Agent 编排" },
  { value: "RAG/知识库", label: "RAG/知识库" },
  { value: "全栈/前端", label: "全栈/前端" },
  { value: "后端/平台", label: "后端/平台" },
  { value: "算法/模型", label: "算法/模型" },
  { value: "通用/后端底子", label: "通用" },
];

const PAGE_SIZE = 20;

export default function JobsPage() {
  const [keyword, setKeyword] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);

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
    api
      .jobs({ keyword: debounced, category, page, size: PAGE_SIZE })
      .then((r) => {
        if (!alive) return;
        setTotal(r.total);
        setItems(r.items);
      })
      .catch(() => {
        if (!alive) return;
        setTotal(0);
        setItems([]);
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [debounced, category, page]);

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">岗位库</h1>
          <p className="mt-2 text-sm text-slate-400">
            共 {total} 条实习岗位{loading && "（加载中…）"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            className="input w-64"
            placeholder="搜索岗位 / 公司 / 技能"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
          <select
            className="input w-40"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-3">
        {items.map((job) => (
          <Link
            key={job.job_id}
            href={`/jobs/${job.job_id}`}
            className="card block p-4 transition-colors hover:border-accent"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="truncate text-base text-slate-100">{job.title}</div>
                <div className="mt-1 text-sm text-slate-400">
                  {job.company} · {job.city}
                  {job.district ? `·${job.district}` : ""} · {job.experience || "-"}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  <span className="tag">{job.category}</span>
                  {job.skills.slice(0, 4).map((s) => (
                    <span key={s} className="tag">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <div className="text-mint">{job.salary || "面议"}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {job.has_jd ? "有 JD" : "无 JD"}
                </div>
              </div>
            </div>
          </Link>
        ))}

        {!loading && items.length === 0 && (
          <div className="card p-8 text-center text-sm text-slate-400">没有匹配的岗位</div>
        )}
      </div>

      <div className="flex items-center justify-end gap-3 text-sm text-slate-400">
        <span>
          第 {page} / {pages} 页
        </span>
        <button
          className="btn btn-ghost disabled:opacity-40"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          上一页
        </button>
        <button
          className="btn btn-ghost disabled:opacity-40"
          disabled={page >= pages}
          onClick={() => setPage((p) => p + 1)}
        >
          下一页
        </button>
      </div>
    </div>
  );
}
