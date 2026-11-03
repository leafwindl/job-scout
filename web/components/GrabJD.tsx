"use client";

import { useRouter } from "next/navigation";
import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";

type Phase = "idle" | "waiting" | "done" | "timeout";

/** 没有 JD 正文时，打开原岗位页让油猴脚本定点抓取这一条。 */
export default function GrabJD({ jobId, url }: { jobId: string; url: string }) {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("idle");
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, []);

  const poll = useCallback(async () => {
    try {
      const job = await api.job(jobId);
      if (job.description && job.description.trim().length > 40) {
        if (timerRef.current) window.clearInterval(timerRef.current);
        setPhase("done");
        setTimeout(() => router.refresh(), 800);
      }
    } catch {
      /* 忽略，继续轮询 */
    }
  }, [jobId, router]);

  function start() {
    if (!url) return;
    const sep = url.includes("?") ? "&" : "?";
    window.open(`${url}${sep}jobscout=one`, "_blank", "noopener");
    setPhase("waiting");
    if (timerRef.current) window.clearInterval(timerRef.current);

    let ticks = 0;
    timerRef.current = window.setInterval(async () => {
      ticks += 1;
      await poll();
      if (ticks >= 30) {
        // 30 次 × 2 秒 = 60 秒
        if (timerRef.current) window.clearInterval(timerRef.current);
        setPhase((p) => (p === "waiting" ? "timeout" : p));
      }
    }, 2000);
  }

  if (phase === "done") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-mint">
        <Sparkles size={12} /> JD 已抓取，刷新中…
      </span>
    );
  }

  if (phase === "timeout") {
    return (
      <div className="flex flex-wrap items-center gap-2 text-xs text-amber-400">
        <span>还没收到正文。确认油猴脚本是 v0.10.3+，并且那个标签页还开着。</span>
        <button className="btn btn-quiet btn-sm" onClick={start}>
          <RefreshCw size={12} /> 再试一次
        </button>
      </div>
    );
  }

  if (phase === "waiting") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-accent">
        <Loader2 size={12} className="animate-spin" />
        已打开原岗位页，等脚本回传正文…（最多 60 秒）
      </span>
    );
  }

  return (
    <button className="btn btn-quiet btn-sm" onClick={start} disabled={!url}>
      <Sparkles size={12} /> 抓取这条 JD
    </button>
  );
}
