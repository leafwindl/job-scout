"use client";

import { useState } from "react";

import { api, type GreetResult, type MatchResult, type RewriteResult } from "@/lib/api";

const VERDICT_STYLE: Record<string, string> = {
  强推: "text-mint border-mint/40 bg-mint/10",
  可投: "text-accent border-accent/40 bg-accent/10",
  观望: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  不建议: "text-rose-400 border-rose-500/40 bg-rose-500/10",
};

function scoreColor(n: number): string {
  if (n >= 80) return "text-mint";
  if (n >= 60) return "text-accent";
  if (n >= 40) return "text-amber-400";
  return "text-rose-400";
}

export default function MatchPanel({ jobId }: { jobId: string }) {
  const [match, setMatch] = useState<MatchResult | null>(null);
  const [greet, setGreet] = useState<GreetResult | null>(null);
  const [rewrite, setRewrite] = useState<RewriteResult | null>(null);
  const [busy, setBusy] = useState<"" | "match" | "greet" | "rewrite">("");
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);

  async function runMatch() {
    setBusy("match");
    setErr("");
    try {
      setMatch(await api.match(jobId));
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy("");
    }
  }

  async function runGreet() {
    setBusy("greet");
    setErr("");
    try {
      const r = await api.greet(jobId);
      setGreet(r);
      setMatch((m) => m ?? { ...r.match, job_id: jobId, title: r.title, company: r.company });
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy("");
    }
  }

  async function runRewrite() {
    setBusy("rewrite");
    setErr("");
    try {
      setRewrite(await api.rewrite(jobId));
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy("");
    }
  }

  async function copyGreeting() {
    if (!greet) return;
    try {
      await navigator.clipboard.writeText(greet.greeting);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setErr("复制失败，请手动选中复制");
    }
  }

  return (
    <div className="card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-medium text-slate-300">投递助手</h2>
        <div className="flex gap-2">
          <button className="btn btn-ghost" onClick={runMatch} disabled={busy !== ""}>
            {busy === "match" ? "分析中…" : "分析匹配度"}
          </button>
          <button className="btn btn-ghost" onClick={runRewrite} disabled={busy !== ""}>
            {busy === "rewrite" ? "生成中…" : "优化简历"}
          </button>
          <button className="btn btn-primary" onClick={runGreet} disabled={busy !== ""}>
            {busy === "greet" ? "生成中…" : "生成打招呼"}
          </button>
        </div>
      </div>

      {err && (
        <div className="mt-3 rounded-lg border border-amber-600/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-400">
          {err.includes("400") ? "还没上传简历，先去「我的」页面上传 PDF" : err}
        </div>
      )}

      {match && (
        <div className="mt-5 space-y-4">
          <div className="flex items-center gap-4">
            <div className={`text-3xl font-semibold tabular-nums ${scoreColor(match.score)}`}>
              {match.score}
            </div>
            <div>
              <span
                className={`inline-block rounded-md border px-2 py-0.5 text-xs ${
                  VERDICT_STYLE[match.verdict] ?? "text-slate-400 border-line"
                }`}
              >
                {match.verdict}
              </span>
              <div className="mt-1 text-xs text-slate-500">{match.reason}</div>
            </div>
          </div>

          {match.matched.length > 0 && (
            <div>
              <div className="mb-1 text-xs text-mint">你具备的</div>
              <ul className="space-y-1 text-sm text-slate-300">
                {match.matched.map((x, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-mint">+</span>
                    <span>{x}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {match.missing.length > 0 && (
            <div>
              <div className="mb-1 text-xs text-rose-400">缺口（面试可能被问）</div>
              <ul className="space-y-1 text-sm text-slate-400">
                {match.missing.map((x, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-rose-400">−</span>
                    <span>{x}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {rewrite && (
        <div className="mt-5 space-y-4 border-t border-line pt-4">
          <div className="text-xs text-slate-500">简历改写建议</div>
          {rewrite.summary && (
            <div className="rounded-lg bg-panel2 p-3 text-sm text-slate-300">
              {rewrite.summary}
            </div>
          )}

          {rewrite.reorder.length > 0 && (
            <div>
              <div className="mb-1 text-xs text-slate-500">项目顺序建议</div>
              <div className="text-sm text-slate-300">
                {rewrite.reorder.map((x, i) => (
                  <span key={i}>
                    {i > 0 && <span className="text-slate-600"> → </span>}
                    {x}
                  </span>
                ))}
              </div>
            </div>
          )}

          {rewrite.rewrites.length > 0 && (
            <div className="space-y-3">
              <div className="text-xs text-slate-500">具体改写</div>
              {rewrite.rewrites.map((r, i) => (
                <div key={i} className="rounded-lg border border-line p-3">
                  {r.project && (
                    <div className="mb-1 text-xs text-slate-500">{r.project}</div>
                  )}
                  {r.original && (
                    <div className="text-sm text-slate-500 line-through">{r.original}</div>
                  )}
                  {r.suggested && (
                    <div className="mt-1 text-sm text-slate-200">{r.suggested}</div>
                  )}
                  {r.why && <div className="mt-1 text-xs text-accent/80">{r.why}</div>}
                </div>
              ))}
            </div>
          )}

          {rewrite.add.length > 0 && (
            <div>
              <div className="mb-1 text-xs text-mint">建议补充</div>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
                {rewrite.add.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            </div>
          )}

          {rewrite.cut.length > 0 && (
            <div>
              <div className="mb-1 text-xs text-rose-400">建议弱化</div>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-400">
                {rewrite.cut.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {greet && (
        <div className="mt-5 border-t border-line pt-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs text-slate-500">
              打招呼消息（{greet.chars} 字）
            </div>
            <button className="btn btn-ghost px-3 py-1 text-xs" onClick={copyGreeting}>
              {copied ? "已复制 ✓" : "复制"}
            </button>
          </div>
          <div className="whitespace-pre-wrap rounded-lg bg-panel2 p-4 text-sm leading-relaxed text-slate-200">
            {greet.greeting}
          </div>
        </div>
      )}
    </div>
  );
}
