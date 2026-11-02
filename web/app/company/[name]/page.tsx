"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowUpRight,
  BarChart3,
  Briefcase,
  Building2,
  Code2,
  Layers,
  MessagesSquare,
  Target,
  Users,
} from "lucide-react";

import { AiLoading } from "@/components/AiLoading";
import { EmptyState, SectionHeader } from "@/components/ui";
import { api, type CompanyProfile } from "@/lib/api";

const PANELS = [
  { key: "business", label: "在做什么", icon: Building2, tone: "accent" },
  { key: "tech_style", label: "技术风格", icon: Code2, tone: "mint" },
  { key: "team", label: "团队特征", icon: Users, tone: "amber" },
  { key: "person_fit", label: "什么人在这里吃香", icon: Target, tone: "rose" },
] as const;

const PANEL_TONE: Record<string, string> = {
  accent: "border-accent/20 bg-accent/[0.06] text-accent",
  mint: "border-mint/20 bg-mint/[0.06] text-mint",
  amber: "border-amber-500/20 bg-amber-500/[0.06] text-amber-400",
  rose: "border-rose-500/20 bg-rose-500/[0.06] text-rose-300",
};

function LoadingView({ name }: { name: string }) {
  return (
    <div className="space-y-5">
      <div className="card p-5 sm:p-6">
        <div className="eyebrow">Company</div>
        <div className="mt-2 skel h-6 w-40" />
        <div className="mt-3 skel h-3 w-64" />
        <div className="mt-2 text-2xs text-fg3">
          正在分析 {name} 的在架岗位与 JD 文本，约 20 秒…
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card space-y-3 p-5">
            <div className="skel h-4 w-24" />
            <div className="skel h-3 w-full" />
            <div className="skel h-3 w-5/6" />
            <div className="skel h-3 w-4/6" />
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="card space-y-3 p-5">
          <div className="skel h-4 w-28" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skel h-3 w-full" />
          ))}
        </div>
        <div className="skel h-64 w-full" />
      </div>
    </div>
  );
}

export default function CompanyPage() {
  const params = useParams<{ name: string }>();
  const name = decodeURIComponent(params?.name ?? "");
  const [data, setData] = useState<CompanyProfile | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [deepLoading, setDeepLoading] = useState(false);

  useEffect(() => {
    if (!name) return;
    let alive = true;
    setLoading(true);
    setErr("");
    setDeepLoading(false);
    setData(null);

    // 第一阶段：统计（信号/技能/岗位列表），毫秒级
    api
      .company(name, false)
      .then((fast) => {
        if (!alive) return;
        setData(fast);
        setLoading(false);
        // 第二阶段：LLM 画像（约 20 秒）
        setDeepLoading(true);
        return api.company(name, true).then((full) => alive && setData(full));
      })
      .catch((e) => alive && setErr(String(e)))
      .finally(() => {
        if (!alive) return;
        setLoading(false);
        setDeepLoading(false);
      });

    return () => {
      alive = false;
    };
  }, [name]);

  if (loading) return <LoadingView name={name} />;

  if (err || !data) {
    return (
      <div className="card">
        <EmptyState
          icon={Building2}
          title={`没找到 ${name} 的在招岗位`}
          description="公司画像需要至少一条带 JD 的岗位，或者这家公司已经停止在架。"
        >
          <Link href="/jobs" className="btn btn-ghost btn-sm">
            <ArrowLeft size={13} /> 返回岗位库
          </Link>
        </EmptyState>
      </div>
    );
  }

  const maxSignal = Math.max(1, ...Object.values(data.signals));
  const skills = [...data.skills].sort((a, b) => b.count - a.count);

  return (
    <div className="space-y-5">
      <Link
        href="/jobs"
        className="inline-flex items-center gap-1.5 text-xs text-fg3 transition-colors hover:text-fg"
      >
        <ArrowLeft size={13} /> 岗位库
      </Link>

      <header className="animate-rise card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="eyebrow">Company</div>
            <h1 className="mt-1.5 text-[24px] font-semibold leading-tight tracking-tight text-fg">
              {data.company}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-fg3">
              <span className="text-fg2">{data.job_count} 个在架实习岗</span>
              <span className="text-fg3/50">·</span>
              <span>{data.districts.join("、") || "地区未知"}</span>
              <span className="text-fg3/50">·</span>
              <span className="tabular-nums text-mint">{data.salary}</span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <a href="#interview" className="btn btn-quiet btn-sm">
              面试会问
            </a>
            <a href="#jobs" className="btn btn-quiet btn-sm">
              在招岗位
            </a>
          </div>
        </div>

        {data.verdict && (
          <div className="mt-4 rounded-lg border border-accent/20 bg-accent/[0.05] px-4 py-3">
            <div className="text-2xs font-medium text-accent">判断</div>
            <p className="mt-1 text-[13px] leading-[1.8] text-fg2">{data.verdict}</p>
          </div>
        )}
      </header>

      {/* 四宫格 */}
      {deepLoading && !data.business ? (
        <AiLoading
          title={`正在分析 ${data.company} 的画像`}
          stages={["读取 JD 文本", "统计行为信号", "推断业务与技术风格", "整理面试重点"]}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {PANELS.map((panel) => {
            const text = data[panel.key];
            if (!text) return null;
            const Icon = panel.icon;
            return (
              <section key={panel.key} className="card p-5">
                <div className="flex items-center gap-2">
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded-md border ${PANEL_TONE[panel.tone]}`}
                  >
                    <Icon size={13} strokeWidth={1.9} />
                  </span>
                  <h2 className="text-[13px] font-medium text-fg">{panel.label}</h2>
                </div>
                <p className="mt-2.5 text-[13px] leading-[1.8] text-fg2">{text}</p>
              </section>
            );
          })}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <div className="space-y-5">
          {deepLoading && !data.interview_focus ? (
            <section id="interview" className="card scroll-mt-24 p-5">
              <SectionHeader title="面试大概会问" icon={MessagesSquare} />
              <div className="mt-3 space-y-2.5">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="skel h-3 w-full" />
                ))}
              </div>
            </section>
          ) : (
            data.interview_focus &&
            data.interview_focus.length > 0 && (
              <section id="interview" className="card scroll-mt-24 p-5">
                <SectionHeader
                  title="面试大概会问"
                  hint={`${data.interview_focus.length} 个方向`}
                  icon={MessagesSquare}
                />
                <ol className="mt-3 space-y-3">
                  {data.interview_focus.map((item, i) => (
                    <li key={i} className="flex gap-3">
                      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-line bg-panel2 text-3xs tabular-nums text-fg3">
                        {i + 1}
                      </span>
                      <p className="text-[13px] leading-[1.75] text-fg2">{item}</p>
                    </li>
                  ))}
                </ol>
              </section>
            )
          )}

          <section id="jobs" className="card scroll-mt-24 overflow-hidden">
            <div className="flex items-center justify-between border-b border-line/60 px-5 py-3.5">
              <SectionHeader
                title="在招岗位"
                hint={`${data.jobs.length} 个`}
                icon={Briefcase}
              />
              <Link href="/jobs" className="text-2xs text-fg3 hover:text-accent">
                全部岗位 →
              </Link>
            </div>
            <div className="divide-y divide-line/60">
              {data.jobs.map((job) => (
                <Link
                  key={job.job_id}
                  href={`/jobs/${job.job_id}`}
                  className="group flex items-center justify-between gap-3 px-5 py-3 transition-colors hover:bg-panel2/40"
                >
                  <span className="min-w-0 truncate text-[13px] text-fg2 group-hover:text-fg">
                    {job.title}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span className="text-2xs tabular-nums text-mint">
                      {job.salary || "面议"}
                    </span>
                    <ArrowUpRight
                      size={13}
                      className="text-fg3 opacity-0 transition-opacity group-hover:opacity-100"
                    />
                  </span>
                </Link>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-5 lg:sticky lg:top-6">
          <section className="card p-5">
            <SectionHeader
              title="行为信号"
              hint="每条 JD 平均命中次数"
              icon={BarChart3}
            />
            <div className="mt-4 space-y-2.5">
              {Object.entries(data.signals).map(([k, v]) => (
                <div key={k}>
                  <div className="flex items-center justify-between gap-2 text-2xs">
                    <span className="truncate text-fg2">{k}</span>
                    <span className="shrink-0 tabular-nums text-fg3">
                      {v.toFixed(1)}
                    </span>
                  </div>
                  <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-panel3/70">
                    <div
                      className="h-full rounded-full bg-accent/80"
                      style={{ width: `${Math.round((v / maxSignal) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
              {Object.keys(data.signals).length === 0 && (
                <p className="text-xs text-fg3">没有可用的行为信号。</p>
              )}
            </div>
          </section>

          <section className="card p-5">
            <SectionHeader title="技能偏好" hint="按命中岗位数" icon={Layers} />
            <div className="mt-3 flex flex-wrap gap-1.5">
              {skills.map((s) => (
                <span key={s.name} className="tag bg-panel2/60">
                  {s.name}
                  <span className="tabular-nums text-fg3">{s.count}</span>
                </span>
              ))}
              {skills.length === 0 && (
                <span className="text-xs text-fg3">没有提取到技能关键词。</span>
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
