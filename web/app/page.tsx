import Link from "next/link";

import { api, type Health, type JobItem, type Profile } from "@/lib/api";

export const dynamic = "force-dynamic";

const ACTIONS = [
  {
    href: "/jobs",
    title: "找工作",
    desc: "按方向、区域筛岗位，点进去看匹配度和缺口",
    accent: true,
  },
  {
    href: "/prep",
    title: "技术准备",
    desc: "该补什么、怎么学、什么不值得学",
  },
  {
    href: "/ask",
    title: "问数据",
    desc: "用自然语言问岗位，回答自带引用",
  },
  {
    href: "/dashboard",
    title: "看板",
    desc: "薪资、技能、区域、方向的整体分布",
  },
];

export default async function HomePage() {
  let health: Health | null = null;
  let profile: Profile | null = null;
  let jobs: JobItem[] = [];
  let total = 0;

  try {
    [health, profile] = await Promise.all([api.health(), api.profile()]);
  } catch {
    health = null;
    profile = null;
  }

  try {
    const page = await api.jobs({ size: 5 });
    total = page.total;
    jobs = page.items;
  } catch {
    jobs = [];
  }

  const ready = Boolean(health);
  const profileReady = Boolean(profile?.uploaded);

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-line bg-gradient-to-br from-panel via-panel to-accent/5 p-8">
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-accent/10 blur-3xl" />
        <div className="relative">
          <div className="text-xs tracking-wider text-accent">JOB SCOUT</div>
          <h1 className="mt-2 text-3xl font-semibold leading-tight">
            把「找工作」变成
            <span className="text-accent">可量化的决策</span>
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-400">
            采集真实招聘 JD，用 RAG 做检索问答；上传简历后给每个岗位打分，
            告诉你值不值得投、差在哪、招呼语怎么写、简历怎么改。
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link href="/jobs" className="btn btn-primary">
              开始找岗位
            </Link>
            {!profileReady && (
              <Link href="/profile" className="btn btn-ghost">
                先上传简历
              </Link>
            )}
            {profileReady && (
              <Link href="/prep" className="btn btn-ghost">
                看技术准备
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* 统计 */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "在架岗位", value: total || "—", unit: "条", hint: "已过滤全职与无关岗位" },
          {
            label: "有 JD 正文",
            value: health?.docs ?? "—",
            unit: "篇",
            hint: "进 RAG 检索语料",
          },
          {
            label: "我的简历",
            value: profileReady ? "已解析" : "未上传",
            unit: "",
            hint: profileReady ? `${profile?.skills?.length ?? 0} 项技能` : "用于匹配打分",
          },
          {
            label: "生成模式",
            value: health?.has_llm ? "LLM" : ready ? "抽取式" : "离线",
            unit: "",
            hint: health?.has_llm ? "已接入模型" : "未配置 Key",
          },
        ].map((s) => (
          <div key={s.label} className="card p-5">
            <div className="text-xs text-slate-500">{s.label}</div>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-semibold tabular-nums">{s.value}</span>
              {s.unit && <span className="text-xs text-slate-500">{s.unit}</span>}
            </div>
            <div className="mt-1 text-xs text-slate-600">{s.hint}</div>
          </div>
        ))}
      </section>

      {/* 快捷入口 */}
      <section>
        <h2 className="mb-3 text-sm font-medium text-slate-300">从这里开始</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {ACTIONS.map((a) => (
            <Link
              key={a.href}
              href={a.href}
              className={`card group p-5 transition-all hover:-translate-y-0.5 hover:border-accent ${
                a.accent ? "border-accent/40" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="text-base font-medium">{a.title}</div>
                <span className="text-slate-600 transition-colors group-hover:text-accent">
                  →
                </span>
              </div>
              <div className="mt-1 text-sm text-slate-400">{a.desc}</div>
            </Link>
          ))}
        </div>
      </section>

      {/* 最新岗位 */}
      {jobs.length > 0 && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-slate-300">最近更新的岗位</h2>
            <Link href="/jobs" className="text-xs text-accent hover:underline">
              查看全部 →
            </Link>
          </div>
          <div className="card divide-y divide-line overflow-hidden">
            {jobs.map((j) => (
              <Link
                key={j.job_id}
                href={`/jobs/${j.job_id}`}
                className="flex items-center justify-between gap-4 px-5 py-3 transition-colors hover:bg-panel2/60"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm text-slate-200">{j.title}</div>
                  <div className="mt-0.5 truncate text-xs text-slate-500">
                    {j.company} · {j.district || j.city}
                  </div>
                </div>
                <div className="shrink-0 text-sm text-mint">{j.salary || "面议"}</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {!ready && (
        <div className="card border-amber-600/40 p-4 text-sm text-amber-400">
          API 未连接。先启动后端：
          <code className="ml-2 rounded bg-panel2 px-2 py-1 text-xs">
            uv run uvicorn api.app.main:app --port 8001
          </code>
        </div>
      )}
    </div>
  );
}
