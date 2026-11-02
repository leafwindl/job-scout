import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  ArrowUpRight,
  Building2,
  Clock3,
  FileText,
  MapPin,
} from "lucide-react";

import MatchPanel from "@/components/MatchPanel";
import { SectionHeader } from "@/components/ui";
import { api, type JobDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let job: JobDetail | null = null;
  try {
    job = await api.job(id);
  } catch {
    job = null;
  }

  if (!job) {
    notFound();
  }

  const location = [job.city, job.district].filter(Boolean).join(" · ");
  const description = (job.description ?? "").replace(/^微信扫码分享\s*举报\s*/, "").trim();

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1.5 text-xs text-fg3 transition-colors hover:text-fg"
        >
          <ArrowLeft size={13} /> 岗位库
        </Link>
        <span className="text-2xs text-fg3">{job.category}</span>
      </div>

      <header className="animate-rise card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-[22px] font-semibold leading-snug tracking-tight text-fg">
              {job.title}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-fg3">
              <Link
                href={`/company/${encodeURIComponent(job.company)}`}
                title="查看公司画像"
                className="inline-flex items-center gap-1.5 text-fg2 transition-colors hover:text-accent"
              >
                <Building2 size={13} strokeWidth={1.9} />
                {job.company}
              </Link>
              {location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin size={13} strokeWidth={1.9} />
                  {location}
                </span>
              )}
              {job.experience && (
                <span className="inline-flex items-center gap-1.5">
                  <Clock3 size={13} strokeWidth={1.9} />
                  {job.experience}
                </span>
              )}
            </div>
          </div>

          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer"
              className="btn btn-soft"
            >
              查看原岗位 <ArrowUpRight size={14} />
            </a>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="rounded-md border border-mint/25 bg-mint/10 px-2 py-1 text-xs font-medium tabular-nums text-mint">
            {job.salary || "面议"}
          </span>
          <span className="tag tag-accent">{job.category}</span>
          <span className={`tag ${job.has_jd ? "tag-mint" : ""}`}>
            {job.has_jd ? "JD 已收录" : "暂无 JD"}
          </span>
          {job.skills.map((skill) => (
            <span key={skill} className="tag">
              {skill}
            </span>
          ))}
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_368px] lg:items-start">
        <section className="card order-2 overflow-hidden lg:order-1">
          <div className="border-b border-line/60 px-5 py-3.5">
            <SectionHeader
              title="岗位描述"
              icon={FileText}
              hint={description ? `约 ${description.length} 字 · 招聘页原文` : "未抓取"}
            />
          </div>
          <div className="px-5 py-5 sm:px-6">
            {description ? (
              <div className="max-w-[75ch] whitespace-pre-wrap text-[13.5px] leading-[1.85] text-fg2">
                {description}
              </div>
            ) : (
              <div className="py-8 text-center">
                <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-panel2 text-fg3">
                  <FileText size={18} strokeWidth={1.7} />
                </div>
                <div className="mt-3 text-[13px] font-medium text-fg">还没有抓取到 JD 正文</div>
                <p className="mx-auto mt-1 max-w-sm text-xs leading-[1.7] text-fg3">
                  岗位本身已入库，但正文缺失。可以先用匹配度看技能要求，或者去「采集任务」补抓一次。
                </p>
                <Link href="/collect" className="btn btn-ghost btn-sm mt-4">
                  去采集任务
                </Link>
              </div>
            )}
          </div>
        </section>

        <aside className="order-1 space-y-4 lg:order-2 lg:sticky lg:top-6 lg:self-start">
          <MatchPanel jobId={job.job_id} />

          <div className="card px-4 py-3.5">
            <div className="text-2xs text-fg3">投递提示</div>
            <p className="mt-1.5 text-xs leading-[1.7] text-fg3">
              先看匹配度再决定是否写招呼语。缺口里的技能，面试大概率会追问；简历建议可以按这个岗位逐条改。
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
