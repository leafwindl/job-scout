"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api, type CompanyProfile } from "@/lib/api";

export default function CompanyPage() {
  const params = useParams<{ name: string }>();
  const name = decodeURIComponent(params?.name ?? "");
  const [data, setData] = useState<CompanyProfile | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!name) return;
    api
      .company(name)
      .then(setData)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [name]);

  if (loading) {
    return (
      <div className="card p-6 text-sm text-slate-400">
        正在分析 {name} 的岗位…（约 20 秒）
      </div>
    );
  }

  if (err || !data) {
    return (
      <div className="card p-6 text-sm text-slate-400">
        没找到这家公司的岗位。
        <Link href="/jobs" className="ml-2 text-accent">
          返回列表
        </Link>
      </div>
    );
  }

  const maxSignal = Math.max(1, ...Object.values(data.signals));

  return (
    <div className="space-y-6">
      <Link href="/jobs" className="text-sm text-slate-400 hover:text-slate-200">
        ← 返回岗位列表
      </Link>

      <div className="card p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{data.company}</h1>
            <div className="mt-2 text-sm text-slate-400">
              {data.job_count} 个在架实习岗 · {data.districts.join("、") || "地区未知"} ·{" "}
              {data.salary}
            </div>
          </div>
          {data.verdict && (
            <span className="rounded-lg border border-accent/40 bg-accent/10 px-3 py-1.5 text-sm text-accent">
              {data.verdict}
            </span>
          )}
        </div>
      </div>

      {(data.business || data.tech_style) && (
        <div className="grid gap-4 md:grid-cols-2">
          {data.business && (
            <div className="card p-5">
              <div className="text-xs text-slate-500">在做什么</div>
              <div className="mt-2 text-sm leading-relaxed text-slate-200">{data.business}</div>
            </div>
          )}
          {data.tech_style && (
            <div className="card p-5">
              <div className="text-xs text-slate-500">技术风格</div>
              <div className="mt-2 text-sm leading-relaxed text-slate-200">{data.tech_style}</div>
            </div>
          )}
          {data.team && (
            <div className="card p-5">
              <div className="text-xs text-slate-500">团队特征</div>
              <div className="mt-2 text-sm leading-relaxed text-slate-200">{data.team}</div>
            </div>
          )}
          {data.person_fit && (
            <div className="card p-5">
              <div className="text-xs text-slate-500">什么人在这里吃香</div>
              <div className="mt-2 text-sm leading-relaxed text-slate-200">{data.person_fit}</div>
            </div>
          )}
        </div>
      )}

      {data.interview_focus && data.interview_focus.length > 0 && (
        <section className="card p-6">
          <h2 className="mb-3 text-sm font-medium text-slate-300">面试大概会问</h2>
          <ul className="space-y-2 text-sm text-slate-300">
            {data.interview_focus.map((x, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-accent">·</span>
                <span>{x}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="card p-6">
        <h2 className="mb-3 text-sm font-medium text-slate-300">
          行为信号 <span className="text-slate-500">（每条 JD 平均命中次数）</span>
        </h2>
        <div className="space-y-1.5">
          {Object.entries(data.signals).map(([k, v]) => (
            <div key={k} className="flex items-center gap-3 text-sm">
              <span className="w-24 text-slate-400">{k}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel2">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${Math.round((v / maxSignal) * 100)}%` }}
                />
              </div>
              <span className="w-10 text-right text-xs tabular-nums text-slate-500">{v}</span>
            </div>
          ))}
        </div>
      </section>

      {data.skills.length > 0 && (
        <section className="card p-6">
          <h2 className="mb-3 text-sm font-medium text-slate-300">技能偏好</h2>
          <div className="flex flex-wrap gap-1.5">
            {data.skills.map((s) => (
              <span key={s.name} className="tag">
                {s.name}
                <span className="ml-1 text-slate-600">{s.count}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      <section className="card p-6">
        <h2 className="mb-3 text-sm font-medium text-slate-300">
          在招岗位 <span className="text-slate-500">（{data.jobs.length}）</span>
        </h2>
        <div className="space-y-2">
          {data.jobs.map((j) => (
            <Link
              key={j.job_id}
              href={`/jobs/${j.job_id}`}
              className="flex items-center justify-between rounded-lg bg-panel2 px-3 py-2 text-sm hover:bg-panel2/70"
            >
              <span className="text-slate-200">{j.title}</span>
              <span className="text-mint">{j.salary || "面议"}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
