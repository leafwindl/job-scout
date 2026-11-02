import { ArrowUpRight, BarChart3, Maximize2 } from "lucide-react";

import PageHeader from "@/components/PageHeader";

export default function DashboardPage() {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Dashboard"
        title="数据看板"
        description="薪资分布、技能词频、方向占比。数据来自已采集的实习岗位，静态页面由 job-scout dashboard 生成。"
        actions={
          <a
            href="/dashboard.html"
            target="_blank"
            rel="noreferrer"
            className="btn btn-ghost"
          >
            <Maximize2 size={14} /> 新窗口打开
          </a>
        }
      />

      <section className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-line/60 px-4 py-2.5">
          <div className="flex min-w-0 items-center gap-2 text-2xs text-fg3">
            <BarChart3 size={13} />
            <span className="truncate">dashboard.html</span>
            <span className="hidden text-fg3/70 sm:inline">· 静态 ECharts</span>
          </div>
          <a
            href="/dashboard.html"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-2xs text-fg3 transition-colors hover:text-accent"
          >
            全屏 <ArrowUpRight size={11} />
          </a>
        </div>
        <iframe
          src="/dashboard.html"
          className="h-[calc(100vh-260px)] min-h-[520px] w-full border-0 bg-ink"
          title="数据看板"
        />
      </section>

      <p className="text-2xs leading-[1.7] text-fg3">
        看板是独立的静态 HTML，样式与 ECharts 配置不在 Next.js 工程内；需要更新数据时重新运行{" "}
        <code className="rounded border border-line bg-panel2 px-1.5 py-0.5 font-mono text-3xs text-mint">
          job-scout dashboard
        </code>{" "}
        再刷新本页。
      </p>
    </div>
  );
}
