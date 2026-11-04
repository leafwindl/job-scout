"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Download,
  ExternalLink,
  Loader2,
  Play,
  RotateCcw,
  Terminal,
} from "lucide-react";

import CollectSettings from "@/components/CollectSettings";
import PageHeader from "@/components/PageHeader";
import { ProgressBar, SectionHeader, Stat } from "@/components/ui";
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
  idle: { label: "未开始", cls: "text-fg3", dot: "bg-fg3" },
  running: { label: "采集中", cls: "text-accent", dot: "bg-accent animate-pulse" },
  done: { label: "已完成", cls: "text-mint", dot: "bg-mint" },
  stalled: { label: "无进展", cls: "text-amber-400", dot: "bg-amber-400" },
};

const CHECKLIST = [
  "新标签页是否真的打开了 BOSS 直聘的岗位列表",
  "浏览器是否装了这个油猴脚本（v0.8.0+）",
  "页面右下角脚本面板是否显示「自动模式：4 秒后开始滚动」",
  "没登录的话先登录，登录后会自动接上",
  "被风控时脚本会等 30 分钟重试，可以先点「重置状态」",
];

function fmtElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function CollectPage() {
  const [keyword, setKeyword] = useState("Agent 实习");
  const [city, setCity] = useState("广州");
  const [intern, setIntern] = useState(true);
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
      const r = await api.collectStart(keyword, city, intern);
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
      <PageHeader
        eyebrow="Collect"
        title="采集任务"
        description="在网页里直接发起采集：打开 BOSS 直聘标签页，油猴脚本自动滚动翻页、抓取 JD，完成后这里实时显示结果。"
        actions={
          status?.state === "done" ? (
            <Link href="/jobs" className="btn btn-primary">
              浏览新岗位 <ArrowUpRight size={15} />
            </Link>
          ) : undefined
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_376px] lg:items-start">
        <div className="order-2 space-y-5 lg:order-1">
          {/* 新建采集 */}
          <section className="animate-rise card p-5">
            <SectionHeader
              title="新建采集"
              hint="关键词 + 城市"
              icon={Download}
            />
            <div className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_140px_auto] sm:items-end">
              <div>
                <label
                  htmlFor="collect-keyword"
                  className="mb-1.5 block text-2xs text-fg3"
                >
                  关键词
                </label>
                <input
                  id="collect-keyword"
                  className="input"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="Agent 实习"
                />
              </div>
              <div>
                <label htmlFor="collect-city" className="mb-1.5 block text-2xs text-fg3">
                  城市
                </label>
                <select
                  id="collect-city"
                  className="select"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                >
                  {CITIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <button
                  className="btn btn-primary flex-1 sm:flex-none"
                  onClick={start}
                  disabled={starting}
                >
                  {starting ? (
                    <>
                      <Loader2 size={14} className="animate-spin" /> 启动中
                    </>
                  ) : (
                    <>
                      <Play size={14} /> 开始采集
                    </>
                  )}
                </button>
                <button className="btn btn-ghost" onClick={reset} title="重置任务状态">
                  <RotateCcw size={14} />
                  <span className="sr-only">重置状态</span>
                </button>
              </div>
            </div>

            <label className="mt-3 flex cursor-pointer items-start gap-2 text-2xs leading-[1.7] text-fg2">
              <input
                type="checkbox"
                checked={intern}
                onChange={(e) => setIntern(e.target.checked)}
                className="mt-0.5 h-3.5 w-3.5 shrink-0 cursor-pointer accent-[#4f8cff]"
              />
              <span>
                只要实习岗
                <span className="text-fg3">
                  （打开搜索页后脚本会自动点选「求职类型 → 实习」；无论如何，接口层只收
                  jobType=4 的岗位）
                </span>
              </span>
            </label>

            <div className="mt-3 flex gap-2 rounded-lg border border-line/60 bg-panel2/30 px-3 py-2.5">
              <ExternalLink size={13} className="mt-0.5 shrink-0 text-fg3" />
              <p className="text-2xs leading-[1.7] text-fg3">
                点击开始会打开一个新的 BOSS 直聘标签页，需要浏览器已装 job-scout 油猴脚本并在登录状态。采集期间可以关掉这个页面。
              </p>
            </div>

            {note && (
              <div className="mt-3 rounded-lg border border-accent/20 bg-accent/[0.05] px-3 py-2 text-2xs leading-[1.7] text-accent">
                {note}
              </div>
            )}
          </section>

          {/* 采集开关（油猴脚本从这里读） */}
          <CollectSettings />

          {/* 排查清单 */}
          <section className="card p-5">
            <SectionHeader
              title="没反应？按顺序检查"
              hint="从最常见的原因开始"
              icon={Terminal}
            />
            <ol className="mt-3 space-y-2">
              {CHECKLIST.map((item, i) => (
                <li key={item} className="flex gap-3">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-line bg-panel2 text-3xs tabular-nums text-fg3">
                    {i + 1}
                  </span>
                  <span className="text-[13px] leading-[1.7] text-fg2">{item}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>

        {/* 状态 */}
        <aside className="order-1 lg:order-2 lg:sticky lg:top-6">
          <section className="card overflow-hidden">
            <div className="flex items-center justify-between border-b border-line/60 px-5 py-3.5">
              <SectionHeader title="采集状态" />
              <span className="inline-flex items-center gap-1.5 text-2xs">
                <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`} />
                <span className={st.cls}>{st.label}</span>
              </span>
            </div>

            <div className="px-5 py-4">
              <p className="text-xs leading-[1.7] text-fg2">
                {status?.message ?? "查询中…"}
              </p>
              <div className="mt-1 flex items-center justify-between text-3xs text-fg3">
                <span>已用 {fmtElapsed(status?.elapsed ?? 0)}</span>
                <span>每 3 秒自动刷新</span>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-line/60 bg-line/50">
                <div className="bg-panel px-3 py-3">
                  <Stat label="库内岗位" value={status?.total ?? "—"} />
                </div>
                <div className="bg-panel px-3 py-3">
                  <Stat
                    label="已抓 JD"
                    value={status?.with_jd ?? "—"}
                    tone="mint"
                  />
                </div>
                <div className="bg-panel px-3 py-3">
                  <Stat
                    label="待抓 JD"
                    value={status?.jd_pending ?? "—"}
                    tone="amber"
                  />
                </div>
              </div>

              <div className="mt-4">
                <div className="mb-1.5 flex justify-between text-2xs text-fg3">
                  <span>JD 抓取进度</span>
                  <span className="tabular-nums text-fg2">{jdPct}%</span>
                </div>
                <ProgressBar value={jdPct} tone="mint" height="h-2" />
              </div>

              {status?.state === "done" && (
                <div className="mt-4 flex gap-2">
                  <Link href="/jobs" className="btn btn-primary btn-sm flex-1">
                    浏览岗位
                  </Link>
                  <Link href="/dashboard" className="btn btn-ghost btn-sm flex-1">
                    打开看板
                  </Link>
                </div>
              )}
            </div>
          </section>

          <div className="mt-3 flex gap-2 rounded-xl border border-line/60 bg-panel2/20 px-4 py-3">
            <Download size={14} className="mt-0.5 shrink-0 text-fg3" />
            <p className="text-2xs leading-[1.7] text-fg3">
              采集只抓公开岗位页面，不绕过登录和验证码。脚本被风控时会自动等待重试。
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
