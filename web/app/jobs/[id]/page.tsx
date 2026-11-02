import Link from "next/link";
import { notFound } from "next/navigation";

import MatchPanel from "@/components/MatchPanel";
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

  return (
    <div className="space-y-6">
      <Link href="/jobs" className="text-sm text-slate-400 hover:text-slate-200">
        ← 返回岗位列表
      </Link>

      <div className="card p-6">
        <h1 className="text-2xl font-semibold">{job.title}</h1>
        <div className="mt-2 text-sm text-slate-400">
          <Link
            href={`/company/${encodeURIComponent(job.company)}`}
            className="text-accent hover:underline"
            title="查看公司画像"
          >
            {job.company}
          </Link>{" "}
          · {job.city}
          {job.district ? `·${job.district}` : ""} · {job.experience || "-"}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="text-lg text-mint">{job.salary || "面议"}</span>
          <span className="tag">{job.category}</span>
          {job.url && (
            <a href={job.url} target="_blank" rel="noreferrer" className="text-sm text-accent">
              查看原岗位 →
            </a>
          )}
        </div>
        {job.skills.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1">
            {job.skills.map((s) => (
              <span key={s} className="tag">
                {s}
              </span>
            ))}
          </div>
        )}
      </div>

      <MatchPanel jobId={job.job_id} />

      <div className="card p-6">
        <h2 className="mb-3 text-sm font-medium text-slate-300">岗位描述</h2>
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
          {job.description || "该岗位尚未抓取到 JD 正文。"}
        </div>
      </div>
    </div>
  );
}
