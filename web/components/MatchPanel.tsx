"use client";

import Link from "next/link";
import { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCheck,
  ChevronDown,
  Copy,
  FileText,
  Loader2,
  MessageSquare,
  Minus,
  Plus,
  RefreshCw,
  Sparkles,
  Target,
  Wand2,
} from "lucide-react";

import { EmptyState } from "@/components/ui";
import { api, type GreetResult, type MatchResult, type RewriteResult } from "@/lib/api";

type TabId = "match" | "greet" | "rewrite";

const VERDICT_STYLE: Record<string, string> = {
  强推: "tag-mint",
  可投: "tag-accent",
  观望: "tag-amber",
  不建议: "tag-rose",
};

function scoreColor(n: number): string {
  if (n >= 80) return "#39d0a8";
  if (n >= 60) return "#4f8cff";
  if (n >= 40) return "#fbbf24";
  return "#fb7185";
}

function ScoreRing({ score }: { score: number }) {
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  const color = scoreColor(score);

  return (
    <div className="relative h-[64px] w-[64px] shrink-0">
      <svg viewBox="0 0 64 64" className="h-[64px] w-[64px] -rotate-90" aria-hidden>
        <circle cx="32" cy="32" r={radius} fill="none" stroke="#202b3d" strokeWidth="5" />
        <circle
          cx="32"
          cy="32"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={
            circumference - (circumference * Math.max(0, Math.min(100, score))) / 100
          }
          className="transition-[stroke-dashoffset] duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-lg font-semibold leading-none tabular-nums"
          style={{ color }}
        >
          {score}
        </span>
        <span className="mt-0.5 text-3xs text-fg3">匹配度</span>
      </div>
    </div>
  );
}

function LoadingPanel({ label }: { label: string }) {
  return (
    <div className="py-6">
      <div className="flex items-center gap-2 text-xs text-fg3">
        <Loader2 size={13} className="animate-spin text-accent" />
        {label}
      </div>
      <div className="mt-4 space-y-2.5">
        <div className="skel h-3.5 w-4/5" />
        <div className="skel h-3.5 w-3/5" />
        <div className="skel h-3.5 w-2/3" />
      </div>
      <p className="mt-4 text-3xs text-fg3">由模型读取 JD 与简历生成，通常需要几秒。</p>
    </div>
  );
}

function MoreButton({
  open,
  rest,
  onClick,
}: {
  open: boolean;
  rest: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-expanded={open}
      className="mt-2 inline-flex items-center gap-1 text-3xs text-fg3 transition-colors hover:text-accent"
    >
      <ChevronDown
        size={11}
        className={`transition-transform ${open ? "rotate-180" : ""}`}
      />
      {open ? "收起" : `展开其余 ${rest} 条`}
    </button>
  );
}

export default function MatchPanel({ jobId }: { jobId: string }) {
  const [tab, setTab] = useState<TabId>("match");
  const [match, setMatch] = useState<MatchResult | null>(null);
  const [greet, setGreet] = useState<GreetResult | null>(null);
  const [rewrite, setRewrite] = useState<RewriteResult | null>(null);
  const [busy, setBusy] = useState<"" | TabId>("");
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);
  // 招呼语：提建议让 AI 重写
  const [feedback, setFeedback] = useState("");
  const [revising, setRevising] = useState(false);
  const [reviseErr, setReviseErr] = useState("");
  const [expanded, setExpanded] = useState({
    matched: false,
    missing: false,
    rewrites: false,
    add: false,
    cut: false,
  });

  function toggle(key: keyof typeof expanded) {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  }

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
      setMatch(
        (m) => m ?? { ...r.match, job_id: jobId, title: r.title, company: r.company },
      );
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

  /** 按用户反馈重写招呼语。 */
  async function reviseGreet() {
    if (!greet || !feedback.trim() || revising) return;
    setRevising(true);
    setReviseErr("");
    try {
      const r = await api.reviseGreet(jobId, greet.greeting, feedback.trim());
      setGreet({
        ...greet,
        greeting: r.greeting,
        chars: r.chars,
      });
      setFeedback("");
    } catch (e) {
      setReviseErr(String(e).slice(0, 120));
    } finally {
      setRevising(false);
    }
  }

  const tabs: { id: TabId; label: string; icon: typeof Target; done: boolean }[] = [
    { id: "match", label: "匹配度", icon: Target, done: Boolean(match) },
    { id: "greet", label: "招呼语", icon: MessageSquare, done: Boolean(greet) },
    { id: "rewrite", label: "简历建议", icon: FileText, done: Boolean(rewrite) },
  ];

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-line/60 px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-accent/25 bg-accent/10 text-accent">
            <Sparkles size={14} strokeWidth={2} />
          </span>
          <div>
            <div className="text-[13px] font-medium text-fg">投递助手</div>
            <div className="text-3xs text-fg3">基于你的简历与这条 JD</div>
          </div>
        </div>
        <span className="tag tag-accent">AI</span>
      </div>

      <div role="tablist" aria-label="投递助手" className="flex gap-1 border-b border-line/60 p-2">
        {tabs.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              role="tab"
              aria-selected={active}
              onClick={() => setTab(t.id)}
              className={`flex h-8 flex-1 items-center justify-center gap-1.5 rounded-md text-xs transition-colors ${
                active
                  ? "bg-panel2 font-medium text-fg"
                  : "text-fg3 hover:bg-panel2/60 hover:text-fg2"
              }`}
            >
              <Icon
                size={13}
                strokeWidth={1.9}
                className={active ? "text-accent" : "text-fg3"}
              />
              {t.label}
              {t.done && <Check size={10} className="text-mint" strokeWidth={2.6} />}
            </button>
          );
        })}
      </div>

      <div role="tabpanel" className="p-4">
        {err && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/[0.06] px-3 py-2.5 text-xs leading-relaxed text-amber-300">
            <AlertTriangle size={13} className="mt-0.5 shrink-0" />
            <span>
              {err.includes("400") ? (
                <>
                  还没上传简历，先去{" "}
                  <Link href="/profile" className="underline underline-offset-2">
                    我的简历
                  </Link>{" "}
                  页上传 PDF。
                </>
              ) : (
                err
              )}
            </span>
          </div>
        )}

        {/* 匹配度 */}
        {tab === "match" &&
          (busy === "match" ? (
            <LoadingPanel label="正在对比简历与 JD…" />
          ) : match ? (
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <ScoreRing score={match.score} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`tag ${VERDICT_STYLE[match.verdict] ?? ""}`}
                    >
                      {match.verdict}
                    </span>
                    <button
                      onClick={runMatch}
                      disabled={busy !== ""}
                      className="ml-auto inline-flex items-center gap-1 text-3xs text-fg3 transition-colors hover:text-accent disabled:opacity-40"
                    >
                      <RefreshCw size={11} /> 重新分析
                    </button>
                  </div>
                  <p className="mt-2 text-xs leading-[1.7] text-fg3">{match.reason}</p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="rounded-lg border border-mint/20 bg-mint/[0.04] p-3">
                  <div className="flex items-center justify-between text-2xs">
                    <span className="inline-flex items-center gap-1.5 text-mint">
                      <Check size={11} strokeWidth={2.5} /> 你具备的
                    </span>
                    <span className="tabular-nums text-fg3">{match.matched.length}</span>
                  </div>
                  {match.matched.length > 0 ? (
                    <>
                      <ul className="mt-2 space-y-2">
                        {(expanded.matched
                          ? match.matched
                          : match.matched.slice(0, 3)
                        ).map((x, i) => (
                          <li
                            key={i}
                            className="flex gap-2 text-xs leading-[1.65] text-fg2"
                          >
                            <Check
                              size={12}
                              strokeWidth={2.4}
                              className="mt-[3px] shrink-0 text-mint"
                            />
                            <span>{x}</span>
                          </li>
                        ))}
                      </ul>
                      {match.matched.length > 3 && (
                        <MoreButton
                          open={expanded.matched}
                          rest={match.matched.length - 3}
                          onClick={() => toggle("matched")}
                        />
                      )}
                    </>
                  ) : (
                    <p className="mt-1.5 text-2xs text-fg3">没有命中岗位明确要求的技能。</p>
                  )}
                </div>

                <div className="rounded-lg border border-rose-500/20 bg-rose-500/[0.04] p-3">
                  <div className="flex items-center justify-between text-2xs">
                    <span className="inline-flex items-center gap-1.5 text-rose-300">
                      <Minus size={11} strokeWidth={2.5} /> 缺口（面试可能被问）
                    </span>
                    <span className="tabular-nums text-fg3">{match.missing.length}</span>
                  </div>
                  {match.missing.length > 0 ? (
                    <>
                      <ul className="mt-2 space-y-2">
                        {(expanded.missing
                          ? match.missing
                          : match.missing.slice(0, 3)
                        ).map((x, i) => (
                          <li
                            key={i}
                            className="flex gap-2 text-xs leading-[1.65] text-fg3"
                          >
                            <Minus
                              size={12}
                              strokeWidth={2.4}
                              className="mt-[3px] shrink-0 text-rose-300"
                            />
                            <span>{x}</span>
                          </li>
                        ))}
                      </ul>
                      {match.missing.length > 3 && (
                        <MoreButton
                          open={expanded.missing}
                          rest={match.missing.length - 3}
                          onClick={() => toggle("missing")}
                        />
                      )}
                    </>
                  ) : (
                    <p className="mt-1.5 text-2xs text-fg3">没发现明显缺口，可以放心投。</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between gap-2 border-t border-line/60 pt-3">
                <span className="text-3xs text-fg3">分析结果仅供参考</span>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    setTab("greet");
                    if (!greet) runGreet();
                  }}
                  disabled={busy !== ""}
                >
                  <MessageSquare size={13} /> 生成招呼语
                </button>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Target}
              title="先看这个岗位值不值得投"
              description="按技能命中、项目相关度和经验要求打分，并列出面试可能被问的缺口。"
              compact
            >
              <button className="btn btn-primary" onClick={runMatch} disabled={busy !== ""}>
                分析匹配度 <ArrowRight size={14} />
              </button>
            </EmptyState>
          ))}

        {/* 招呼语 */}
        {tab === "greet" &&
          (busy === "greet" ? (
            <LoadingPanel label="正在写打招呼消息…" />
          ) : greet ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex flex-wrap items-center gap-2 text-2xs text-fg3">
                  <MessageSquare size={12} />
                  <span className={greet.chars > 200 ? "text-amber-400" : ""}>
                    {greet.chars} 字{greet.chars > 200 ? "（超 200）" : ""}
                  </span>
                  {greet.used_code && (
                    <span className="tag tag-mint" title="生成时参考了你提交的项目代码">
                      含代码事实
                    </span>
                  )}
                  {match && (
                    <span className="tag tag-accent">{match.score} 分 · {match.verdict}</span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={copyGreeting}
                    aria-live="polite"
                  >
                    {copied ? (
                      <>
                        <CheckCheck size={13} className="text-mint" /> 已复制
                      </>
                    ) : (
                      <>
                        <Copy size={13} /> 复制
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="whitespace-pre-wrap rounded-lg border border-line bg-panel2/40 p-4 text-[13.5px] leading-[1.8] text-fg">
                {greet.greeting}
              </div>

              <div className="flex items-center justify-between border-t border-line/60 pt-3">
                <button
                  className="btn btn-quiet btn-sm"
                  onClick={runGreet}
                  disabled={busy !== "" || revising}
                >
                  <RefreshCw size={12} /> 换一条
                </button>
                <span className="text-3xs text-fg3">发送前建议按自己的语气再改两句</span>
              </div>

              {/* 提建议让 AI 重写 */}
              <div className="rounded-lg border border-line/60 bg-panel2/30 p-2.5">
                <div className="mb-1.5 text-2xs text-fg3">不满意？说哪里不对，让它改</div>
                <div className="flex gap-1.5">
                  <input
                    className="input h-8 flex-1 py-0 text-xs"
                    placeholder="比如：太长了 / 别提薪资 / 强调 RAG 项目"
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") reviseGreet();
                    }}
                    disabled={revising}
                  />
                  <button
                    className="btn btn-ghost btn-sm shrink-0"
                    onClick={reviseGreet}
                    disabled={!feedback.trim() || revising}
                  >
                    {revising ? (
                      <>
                        <Loader2 size={12} className="animate-spin" /> 改中
                      </>
                    ) : (
                      <>
                        <Wand2 size={12} /> 按建议重写
                      </>
                    )}
                  </button>
                </div>
                {reviseErr && <p className="mt-1.5 text-2xs text-rose-400">{reviseErr}</p>}
              </div>
            </div>
          ) : (
            <EmptyState
              icon={MessageSquare}
              title="生成一条不尴尬的招呼语"
              description="引用你项目里和岗位要求重合的部分，控制在 HR 一屏能读完的长度。"
              compact
            >
              <button className="btn btn-primary" onClick={runGreet} disabled={busy !== ""}>
                生成打招呼 <ArrowRight size={14} />
              </button>
            </EmptyState>
          ))}

        {/* 简历建议 */}
        {tab === "rewrite" &&
          (busy === "rewrite" ? (
            <LoadingPanel label="正在按 JD 重排简历…" />
          ) : rewrite ? (
            <div className="space-y-4">
              {rewrite.used_code && (
                <div className="flex items-center gap-1.5 rounded-lg border border-mint/25 bg-mint/[0.06] px-3 py-2 text-2xs text-mint">
                  <Check size={11} /> 已参考你提交的项目代码
                </div>
              )}
              {rewrite.summary && (
                <p className="rounded-lg border border-accent/20 bg-accent/[0.05] px-3 py-2.5 text-xs leading-[1.7] text-fg2">
                  {rewrite.summary}
                </p>
              )}

              {rewrite.reorder.length > 0 && (
                <div>
                  <div className="mb-1.5 text-2xs text-fg3">项目顺序建议</div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {rewrite.reorder.map((x, i) => (
                      <span key={i} className="flex items-center gap-1.5">
                        {i > 0 && <ArrowRight size={11} className="text-fg3" />}
                        <span className="tag">{x}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {rewrite.rewrites.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="text-2xs text-fg3">具体改写</div>
                    <span className="text-3xs tabular-nums text-fg3">
                      {rewrite.rewrites.length} 条
                    </span>
                  </div>
                  {(expanded.rewrites
                    ? rewrite.rewrites
                    : rewrite.rewrites.slice(0, 2)
                  ).map((r, i) => (
                    <div key={i} className="card-inset p-3">
                      {r.project && (
                        <div className="mb-1.5 text-2xs text-fg3">{r.project}</div>
                      )}
                      {r.original && (
                        <div className="text-xs leading-[1.7] text-fg3 line-through decoration-line">
                          {r.original}
                        </div>
                      )}
                      {r.suggested && (
                        <div className="mt-1 text-[13px] leading-[1.7] text-fg">
                          {r.suggested}
                        </div>
                      )}
                      {r.why && (
                        <div className="mt-1.5 text-[12px] leading-[1.7] text-accent/80">
                          {r.why}
                        </div>
                      )}
                    </div>
                  ))}
                  {rewrite.rewrites.length > 2 && (
                    <MoreButton
                      open={expanded.rewrites}
                      rest={rewrite.rewrites.length - 2}
                      onClick={() => toggle("rewrites")}
                    />
                  )}
                </div>
              )}

              {(rewrite.add.length > 0 || rewrite.cut.length > 0) && (
                <div className="space-y-2">
                  {rewrite.add.length > 0 && (
                    <div className="rounded-lg border border-mint/20 bg-mint/[0.04] p-3">
                      <div className="inline-flex items-center gap-1.5 text-2xs text-mint">
                        <Plus size={11} /> 建议补充
                      </div>
                      <ul className="mt-2 space-y-2">
                        {(expanded.add ? rewrite.add : rewrite.add.slice(0, 3)).map(
                          (x, i) => (
                            <li key={i} className="flex gap-2 text-xs leading-[1.65] text-fg2">
                              <Plus size={12} className="mt-[3px] shrink-0 text-mint" />
                              <span>{x}</span>
                            </li>
                          ),
                        )}
                      </ul>
                      {rewrite.add.length > 3 && (
                        <MoreButton
                          open={expanded.add}
                          rest={rewrite.add.length - 3}
                          onClick={() => toggle("add")}
                        />
                      )}
                    </div>
                  )}
                  {rewrite.cut.length > 0 && (
                    <div className="rounded-lg border border-rose-500/20 bg-rose-500/[0.04] p-3">
                      <div className="inline-flex items-center gap-1.5 text-2xs text-rose-300">
                        <Minus size={11} /> 建议弱化
                      </div>
                      <ul className="mt-2 space-y-2">
                        {(expanded.cut ? rewrite.cut : rewrite.cut.slice(0, 3)).map(
                          (x, i) => (
                            <li key={i} className="flex gap-2 text-xs leading-[1.65] text-fg3">
                              <Minus size={12} className="mt-[3px] shrink-0 text-rose-300" />
                              <span>{x}</span>
                            </li>
                          ),
                        )}
                      </ul>
                      {rewrite.cut.length > 3 && (
                        <MoreButton
                          open={expanded.cut}
                          rest={rewrite.cut.length - 3}
                          onClick={() => toggle("cut")}
                        />
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between border-t border-line/60 pt-3">
                <button
                  className="btn btn-quiet btn-sm"
                  onClick={runRewrite}
                  disabled={busy !== ""}
                >
                  <RefreshCw size={12} /> 重新生成
                </button>
                <Link href="/prep" className="text-2xs text-accent hover:underline">
                  看该补哪些技术 →
                </Link>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={FileText}
              title="按这个岗位重排简历"
              description="给出项目顺序、逐条改写、该补充什么、该弱化什么，针对这条 JD。"
              compact
            >
              <button className="btn btn-primary" onClick={runRewrite} disabled={busy !== ""}>
                优化简历 <ArrowRight size={14} />
              </button>
            </EmptyState>
          ))}
      </div>
    </div>
  );
}
