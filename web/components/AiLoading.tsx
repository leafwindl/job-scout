"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

/** AI 分析进行中的占位：带秒数计数和阶段文案，让长等待可感知。 */
export function AiLoading({
  title = "AI 正在分析",
  stages = ["读取岗位要求", "对比你的技能", "生成建议"],
  compact = false,
  /** 预估总耗时（秒），用来把阶段均分到时间轴上 */
  estimatedSeconds = 20,
  hint,
}: {
  title?: string;
  stages?: string[];
  compact?: boolean;
  estimatedSeconds?: number;
  hint?: string;
}) {
  const [sec, setSec] = useState(0);

  useEffect(() => {
    const t = window.setInterval(() => setSec((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, []);

  // 预估时长均分到各阶段，超出后停在最后一步
  const per = estimatedSeconds / Math.max(1, stages.length);
  const idx = Math.min(stages.length - 1, Math.floor(sec / per));

  return (
    <div
      className={`flex flex-col items-center justify-center rounded-xl border border-line/60 bg-panel2/40 text-center ${
        compact ? "px-5 py-6" : "px-6 py-10"
      }`}
    >
      <div className="relative flex h-9 w-9 items-center justify-center">
        <Sparkles size={16} strokeWidth={1.8} className="text-accent/70" />
        <Loader2
          size={30}
          strokeWidth={2}
          className="absolute animate-spin text-accent/40"
        />
      </div>
      <div className="mt-3 text-[13px] font-medium text-fg">{title}</div>
      <div className="mt-1 text-xs text-fg3">
        {stages[idx]}…
        <span className="ml-1 tabular-nums text-fg3/70">{sec}s</span>
      </div>
      <div className="mt-3 flex gap-1">
        {stages.map((s, i) => (
          <span
            key={s}
            className={`h-1 w-8 rounded-full transition-colors ${
              i <= idx ? "bg-accent/60" : "bg-line"
            }`}
          />
        ))}
      </div>
      {hint && <p className="mt-3 max-w-xs text-3xs leading-[1.7] text-fg3">{hint}</p>}
    </div>
  );
}
