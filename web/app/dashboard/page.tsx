export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">数据看板</h1>
          <p className="mt-2 text-sm text-slate-400">
            薪资分布、技能词频、方向占比。数据来自已采集的 200 条实习岗位。
          </p>
        </div>
        <a href="/dashboard.html" target="_blank" rel="noreferrer" className="btn btn-ghost">
          新窗口打开
        </a>
      </div>

      <div className="card overflow-hidden">
        <iframe src="/dashboard.html" className="h-[82vh] w-full border-0" title="数据看板" />
      </div>
    </div>
  );
}
