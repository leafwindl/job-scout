"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, type CollectStatus } from "@/lib/api";

const CITIES = [
  "广州",
  "深圳",
  "北京",
  "上海",
  "杭州",
  "成都",
  "武汉",
  "南京",
  "西安",
  "苏州",
  "长沙",
  "东莞",
  "佛山",
  "珠海",
  "厦门",
];

const STATE_STYLE: Record<string, { label: string; cls: string; dot: string }> = {
  idle: { label: "未开始", cls: "text-slate-400", dot: "bg-slate-500" },
  running: { label: "采集中", cls: "text-accent", dot: "bg-accent animate-pulse" },
  done: { label: "已完成", cls: "text-mint", dot: "bg-mint" },
  stalled: { label: "无进展", cls: "text-amber-400", dot: "bg-amber-400" },
};

function fmtElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function CollectPage() {
  const [keyword, setKeyword] = useState("Agent 实习");
  const [city, setCity] = useState("广州");
  const [status, setStatus] = useState<CollectStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [note, setNote] = useState("");
  const timer = useRef<number | null>(null);

  const poll = useCallback(async () => {
    try {
      setStatus(await api.collectStatus());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    poll();
    timer.current = window.setInterval(poll, 3000);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [poll]);

  async function start() {
    setStarting(true);
    setNote("");
    // 先同步开窗口，避免 await 之后被弹窗拦截
    const win = window.open("about:blank", "_blank");
    try {
      const r = await api.collectStart(keyword, city);
      if (win) {
        win.location.href = r.url;
        setNote("已打开新标签页，脚本会自动开始。不用时可关掉。");
      } else {
        setNote(`弹窗被拦截，请手动打开：${r.url}`);
      }
      await poll();
    } catch (e) {
      win?.close();
      setNote(`启动失败：${String(e)}`);
    } finally {
      setStarting(false);
    }
  }

  async function reset() {
    await api.collectReset().catch(() => undefined);
    await poll();
    setNote("已重置任务状态（数据不变）");
  }

  const st = status ? STATE_STYLE[status.state] ?? STATE_STYLE.idle : STATE_STYLE.idle;
  const jdTotal = status ? status.with_jd + status.jd_pending : 0;
  const jdPct = jdTotal > 0 && status ? Math.round((status.with_jd / jdTotal) * 100) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">采集</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          在网页里直接发起采集。点「开始采集」会打开一个新的 BOSS 直聘标签页，
          油猴脚本检测到自动模式后开始滚动翻页、抓取 JD，完成后这里会实时显示结果。
        </p>
      </div>

      <div className="card p-5">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <div className="mb-1 text-xs text-slate-500">关键词</div>
            <input
              className="input w-56"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="Agent 实习"
            />
          </div>
          <div>
            <div className="mb-1 text-xs text-slate-500">城市</div>
            <select className="input w-32" value={city} onChange={(e) => setCity(e.target.value)}>
              {CITIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={start} disabled={starting}>
            {starting ? "启动中…" : "开始采集"}
          </button>
          <button className="btn btn-ghost" onClick={reset}>
            重置状态
          </button>
        </div>

        {note && <div className="mt-3 text-xs text-slate-400">{note}</div>}
      </div>

      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${st.dot}`} />
            <span className={`text-sm font-medium ${st.cls}`}>{st.label}</span>
          </div>
          <div className="text-xs text-slate-500">
            已用 {fmtElapsed(status?.elapsed ?? 0)}
          </div>
        </div>

        <div className="mt-2 text-sm text-slate-400">
          {status?.message ?? "查询中…"}
        </div>

        <div className="mt-5 grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-slate-500">库内岗位</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">
              {status?.total ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">已抓 JD</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-mint">
              {status?.with_jd ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">待抓 JD</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-amber-400">
              {status?.jd_pending ?? "—"}
            </div>
          </div>
        </div>

        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs text-slate-500">
            <span>JD 抓取进度</span>
            <span>{jdPct}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-panel2">
            <div
              className="h-full rounded-full bg-mint transition-all duration-500"
              style={{ width: `${jdPct}%` }}
            />
          </div>
        </div>

        {status?.state === "done" && (
          <div className="mt-5 flex gap-3">
            <Link href="/jobs" className="btn btn-primary">
              浏览岗位
            </Link>
            <Link href="/dashboard" className="btn btn-ghost">
              打开看板
            </Link>
          </div>
        )}
      </div>

      <div className="card border-line p-5 text-sm text-slate-400">
        <div className="mb-2 text-slate-300">没反应？按顺序检查</div>
        <ol className="list-decimal space-y-1 pl-5">
          <li>新标签页是否真的打开了 BOSS 直聘的岗位列表</li>
          <li>浏览器是否装了这个油猴脚本（v0.8.0+）</li>
          <li>页面右下角脚本面板是否显示「自动模式：4 秒后开始滚动」</li>
          <li>没登录的话先登录，登录后会自动接上</li>
          <li>被风控时脚本会等 30 分钟重试，可以先点「重置状态」</li>
        </ol>
      </div>
    </div>
  );
}
