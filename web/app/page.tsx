import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Check,
  Download,
  FileText,
  FlaskConical,
  MessagesSquare,
  Sparkles,
} from "lucide-react";

import JobRow from "@/components/JobRow";
import PageHeader from "@/components/PageHeader";
import { SectionHeader, Stat } from "@/components/ui";
import { api, type Health, type JobItem, type Profile } from "@/lib/api";

export const dynamic = "force-dynamic";

const TOOLS = [
  { href: "/prep", label: "技术准备", desc: "该补什么", icon: BookOpen },
  { href: "/ask", label: "智能问答", desc: "问岗位数据", icon: MessagesSquare },
  { href: "/collect", label: "采集任务", desc: "抓取新 JD", icon: Download },
  { href: "/dashboard", label: "数据看板", desc: "薪资与技能分布", icon: BarChart3 },
  { href: "/eval", label: "检索评测", desc: "RAG 指标", icon: FlaskConical },
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
    const page = await api.jobs({ size: 6 });
    total = page.total;
    jobs = page.items;
  } catch {
    jobs = [];
  }

  const ready = Boolean(health);
  const profileReady = Boolean(profile?.uploaded);
  const skillCount = profile?.skills?.length ?? 0;
  const projectCount = profile?.projects?.length ?? 0;

  const steps = [
    {
      title: "上传 PDF 简历",
      desc: profileReady ? "已解析技能与项目经历" : "用于匹配打分和招呼语生成",
      href: "/profile",
      done: profileReady,
    },
    {
      title: "挑 3 个值得投的岗位",
      desc: `${total || "—"} 个在架实习岗，按方向和关键词筛`,
      href: "/jobs",
      done: false,
    },
    {
      title: "生成打招呼消息",
      desc: "在岗位详情页右侧，一键复制",
      href: "/jobs",
      done: false,
    },
    {
      title: "补齐技术要求",
      desc: "按性价比排序，知道先学什么",
      href: "/prep",
      done: false,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Workspace"
        title={profile?.name ? `概览 · ${profile.name}` : "概览"}
        description="把求职变成可执行的决策：今天投什么、差在哪、下一步补什么。"
        actions={
          <>
            <Link href="/jobs" className="btn btn-primary">
              浏览岗位 <ArrowRight size={15} />
            </Link>
            <Link href="/collect" className="btn btn-ghost">
              <Download size={15} /> 采集新岗位
            </Link>
          </>
        }
      />

      {!ready && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/[0.06] px-4 py-3 text-[13px] text-amber-300">
          <span className="font-medium">API 未连接</span>
          <span className="text-amber-300/80">先启动后端：</span>
          <code className="rounded border border-amber-500/20 bg-panel2 px-2 py-0.5 font-mono text-2xs text-amber-200">
            uv run uvicorn api.app.main:app --port 8001
          </code>
        </div>
      )}

      {/* 今日概览 + 指标 */}
      <section className="animate-rise card overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-line/60 px-5 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-2xs text-fg3">
              <Sparkles size={12} className="text-accent" />
              今日概览
            </div>
            <h2 className="mt-2 text-[17px] font-medium leading-snug text-fg">
              {profileReady
                ? `简历已就绪，从 ${total || "—"} 个岗位里挑出最值得投的`
                : "先上传简历，让每个岗位都有匹配分"}
            </h2>
            <p className="mt-1.5 max-w-xl text-[13px] leading-[1.7] text-fg3">
              {profileReady
                ? `已识别 ${skillCount} 项技能、${projectCount} 个项目；在岗位详情页可以看缺口、改写建议和招呼语。`
                : "上传 PDF 后自动提取技能和项目经历，用于匹配打分与招呼语生成。"}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-2">
            <Link
              href={profileReady ? "/prep" : "/profile"}
              className="btn btn-soft"
            >
              {profileReady ? "看该补什么" : "上传简历"}
            </Link>
            <Link href="/ask" className="btn btn-quiet">
              去问数据 <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-px bg-line/50 sm:grid-cols-4">
          <div className="bg-panel px-5 py-4">
            <Stat label="在架岗位" value={total || "—"} unit="条" hint="已过滤无关岗位" />
          </div>
          <div className="bg-panel px-5 py-4">
            <Stat
              label="可检索 JD"
              value={health?.docs ?? "—"}
              unit="篇"
              hint="进入 RAG 语料"
              tone="mint"
            />
          </div>
          <div className="bg-panel px-5 py-4">
            <Stat
              label="我的简历"
              value={profileReady ? "已解析" : "未上传"}
              hint={profileReady ? `${skillCount} 项技能 · ${projectCount} 个项目` : "上传 PDF 解锁匹配"}
              tone={profileReady ? "mint" : "amber"}
            />
          </div>
          <div className="bg-panel px-5 py-4">
            <Stat
              label="生成模式"
              value={health?.has_llm ? "LLM" : ready ? "抽取式" : "离线"}
              hint={health?.has_llm ? "已接入模型" : "未配置 Key"}
              tone="accent"
            />
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_312px]">
        {/* 最近岗位 */}
        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-line/60 px-5 py-3.5">
            <SectionHeader
              title="最近更新的岗位"
              hint={jobs.length > 0 ? `展示 ${jobs.length} 条` : undefined}
            />
            <Link
              href="/jobs"
              className="inline-flex items-center gap-1 text-2xs text-fg3 transition-colors hover:text-accent"
            >
              查看全部 <ArrowRight size={12} />
            </Link>
          </div>

          {jobs.length > 0 ? (
            <div className="divide-y divide-line/60">
              {jobs.map((job) => (
                <JobRow key={job.job_id} job={job} />
              ))}
            </div>
          ) : (
            <div className="px-5 py-10 text-center text-[13px] text-fg3">
              还没有岗位数据，先去「采集任务」抓一批。
            </div>
          )}
        </section>

        {/* 右栏 */}
        <aside className="space-y-6">
          <section className="card">
            <div className="flex items-center justify-between border-b border-line/60 px-5 py-3.5">
              <SectionHeader title="你的求职档案" />
              <Link href="/profile" className="text-2xs text-fg3 hover:text-accent">
                管理
              </Link>
            </div>
            <div className="px-5 py-4">
              {profileReady ? (
                <>
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full border border-accent/25 bg-accent/10 text-[13px] font-medium text-accent">
                      {profile?.name?.slice(0, 1) || "简"}
                    </span>
                    <div className="min-w-0">
                      <div className="truncate text-[13px] font-medium text-fg">
                        {profile?.name || "未识别姓名"}
                      </div>
                      <div className="truncate text-2xs text-fg3">
                        {profile?.target || "未填写求职方向"}
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {(profile?.skills ?? []).slice(0, 6).map((skill) => (
                      <span key={skill} className="tag">
                        {skill}
                      </span>
                    ))}
                    {skillCount > 6 && (
                      <span className="tag text-fg3">+{skillCount - 6}</span>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-panel2 text-fg3">
                      <FileText size={15} />
                    </span>
                    <div className="min-w-0">
                      <div className="text-[13px] font-medium text-fg">还没有简历</div>
                      <div className="text-2xs text-fg3">匹配度、招呼语都依赖它</div>
                    </div>
                  </div>
                  <Link href="/profile" className="btn btn-primary btn-sm mt-4 w-full">
                    上传 PDF 简历
                  </Link>
                </>
              )}
            </div>
          </section>

          <section className="card">
            <div className="border-b border-line/60 px-5 py-3.5">
              <SectionHeader title="求职路径" hint="从简历到投递" />
            </div>
            <ol className="space-y-1 px-3 py-3">
              {steps.map((step, index) => (
                <li key={step.title}>
                  <Link
                    href={step.href}
                    className="group flex gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-panel2/50"
                  >
                    <span
                      className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-2xs font-medium ${
                        step.done
                          ? "border-mint/30 bg-mint/10 text-mint"
                          : "border-line bg-panel2 text-fg3"
                      }`}
                    >
                      {step.done ? <Check size={12} strokeWidth={2.5} /> : index + 1}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span
                          className={`text-[13px] ${
                            step.done ? "text-fg3 line-through decoration-line" : "text-fg"
                          }`}
                        >
                          {step.title}
                        </span>
                        <ArrowRight
                          size={13}
                          className="shrink-0 text-fg3 opacity-0 transition-opacity group-hover:opacity-100"
                        />
                      </span>
                      <span className="mt-0.5 block text-2xs leading-4 text-fg3">
                        {step.desc}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          </section>

          <section className="card overflow-hidden">
            <div className="border-b border-line/60 px-5 py-3.5">
              <SectionHeader title="工具" />
            </div>
            <div className="p-1.5">
              {TOOLS.map((tool) => {
                const Icon = tool.icon;
                return (
                  <Link
                    key={tool.href}
                    href={tool.href}
                    className="group flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-panel2/50"
                  >
                    <Icon size={15} strokeWidth={1.8} className="text-fg3" />
                    <span className="flex-1 text-[13px] text-fg2 group-hover:text-fg">
                      {tool.label}
                    </span>
                    <span className="text-2xs text-fg3">{tool.desc}</span>
                  </Link>
                );
              })}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
