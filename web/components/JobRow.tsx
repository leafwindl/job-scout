import Link from "next/link";
import { ArrowUpRight, Clock3, FileText, MapPin } from "lucide-react";

import type { JobItem } from "@/lib/api";

const AVATAR_TONES = [
  "border-accent/25 bg-accent/10 text-accent",
  "border-mint/25 bg-mint/10 text-mint",
  "border-amber-500/25 bg-amber-500/10 text-amber-400",
  "border-rose-500/25 bg-rose-500/10 text-rose-400",
];

function avatarTone(name: string): string {
  let sum = 0;
  for (let i = 0; i < name.length; i += 1) sum += name.charCodeAt(i);
  return AVATAR_TONES[sum % AVATAR_TONES.length];
}

export function JobRowSkeleton() {
  return (
    <div className="flex items-start gap-4 px-4 py-4 sm:px-5">
      <div className="skel hidden h-9 w-9 shrink-0 sm:block" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="skel h-3.5 w-1/2" />
        <div className="skel h-3 w-2/5" />
        <div className="flex gap-1.5 pt-1">
          <div className="skel h-4 w-12" />
          <div className="skel h-4 w-14" />
          <div className="skel h-4 w-10" />
        </div>
      </div>
      <div className="skel h-3.5 w-16 shrink-0" />
    </div>
  );
}

export default function JobRow({
  job,
  showTags = true,
}: {
  job: JobItem;
  showTags?: boolean;
}) {
  const location = [job.city, job.district].filter(Boolean).join(" · ");

  return (
    <Link
      href={`/jobs/${job.job_id}`}
      className="group flex items-start gap-3 px-4 py-4 transition-colors hover:bg-panel2/40 sm:gap-4 sm:px-5"
    >
      <span
        className={`mt-0.5 hidden h-9 w-9 shrink-0 items-center justify-center rounded-lg border text-[13px] font-semibold sm:flex ${avatarTone(
          job.company,
        )}`}
      >
        {job.company.slice(0, 1)}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-[14px] font-medium text-fg group-hover:text-white">
              {job.title}
            </h3>
            <div className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-2xs text-fg3">
              <span className="truncate text-fg2">{job.company}</span>
              {location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin size={11} strokeWidth={2} />
                  {location}
                </span>
              )}
              {job.experience && (
                <span className="inline-flex items-center gap-1">
                  <Clock3 size={11} strokeWidth={2} />
                  {job.experience}
                </span>
              )}
              <span className="hidden items-center gap-1 sm:inline-flex">
                <FileText size={11} strokeWidth={2} />
                {job.has_jd ? "JD 已收录" : "暂无 JD"}
              </span>
            </div>
          </div>

          <div className="shrink-0 text-right">
            <div className="text-[13px] font-medium tabular-nums text-mint">
              {job.salary || "面议"}
            </div>
            <div className="mt-1 hidden text-3xs text-fg3 sm:block">{job.category}</div>
          </div>
        </div>

        {showTags && (
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            <span className="tag border-line/70 bg-panel2/50 text-fg3 sm:hidden">
              {job.category}
            </span>
            {job.skills.slice(0, 5).map((skill) => (
              <span key={skill} className="tag">
                {skill}
              </span>
            ))}
            {job.skills.length > 5 && (
              <span className="text-3xs text-fg3">+{job.skills.length - 5}</span>
            )}
          </div>
        )}
      </div>

      <ArrowUpRight
        size={15}
        className="mt-1 hidden shrink-0 text-fg3 opacity-0 transition-opacity group-hover:opacity-100 lg:block"
      />
    </Link>
  );
}
