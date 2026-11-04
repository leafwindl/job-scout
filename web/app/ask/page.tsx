"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUpRight,
  Loader2,
  Quote,
  Radar,
  RotateCcw,
  Send,
  Sparkles,
  StopCircle,
  UserRound,
} from "lucide-react";

import PageHeader from "@/components/PageHeader";
import { API_BASE, type Citation } from "@/lib/api";

type Msg = {
  role: "user" | "assistant";
  text: string;
  citations: Citation[];
  pending?: boolean;
};

/** 把回答里的 [1][2] 变成可点击锚点，跳到对应引用卡片。 */
function linkifyCitations(text: string, messageIndex: number): string {
  return text.replace(
    /\[(\d+)\]/g,
    (_m, n: string) => `[[${n}]](#cite-${messageIndex}-${n})`,
  );
}

function patchLast(list: Msg[], fn: (m: Msg) => Msg): Msg[] {
  if (!list.length) return list;
  const next = list.slice();
  next[next.length - 1] = fn(next[next.length - 1]);
  return next;
}

const EXAMPLES = [
  "哪些实习岗要求 LangGraph？",
  "安点科技的实习岗要什么技能？",
  "海珠区有 RAG 相关的实习吗？",
];

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [useProfile, setUseProfile] = useState(false);
  const [topK, setTopK] = useState(8);
  const esRef = useRef<EventSource | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // 记住上次的选择
  useEffect(() => {
    try {
      setUseProfile(localStorage.getItem("jobscout.askProfile") === "1");
      const savedK = Number(localStorage.getItem("jobscout.askK"));
      if (savedK >= 3 && savedK <= 20) setTopK(savedK);
    } catch {
      /* ignore */
    }
  }, []);

  function toggleProfile(next: boolean) {
    setUseProfile(next);
    try {
      localStorage.setItem("jobscout.askProfile", next ? "1" : "0");
    } catch {
      /* ignore */
    }
  }

  function changeK(next: number) {
    setTopK(next);
    try {
      localStorage.setItem("jobscout.askK", String(next));
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (msgs.length > 0) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [msgs.length]);

  useEffect(() => {
    if (!busy && msgs.length > 0) {
      endRef.current?.scrollIntoView({ block: "end" });
    }
  }, [busy, msgs.length]);

  function stop() {
    esRef.current?.close();
    esRef.current = null;
    setBusy(false);
    setMsgs((m) => patchLast(m, (x) => ({ ...x, pending: false })));
  }

  function reset() {
    stop();
    setMsgs([]);
    setQuestion("");
  }

  function send(q: string) {
    const text = q.trim();
    if (!text || busy) return;

    setBusy(true);
    setQuestion("");
    setMsgs((m) => [
      ...m,
      { role: "user", text, citations: [] },
      { role: "assistant", text: "", citations: [], pending: true },
    ]);

    const es = new EventSource(
      `${API_BASE}/ask/stream?q=${encodeURIComponent(text)}&k=${topK}&use_profile=${
        useProfile ? 1 : 0
      }`,
    );
    esRef.current = es;

    es.addEventListener("meta", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as { candidates: Citation[] };
      setMsgs((m) =>
        patchLast(m, (x) => ({ ...x, citations: data.candidates ?? [] })),
      );
    });

    es.addEventListener("token", (e) => {
      const token = JSON.parse((e as MessageEvent).data) as string;
      setMsgs((m) =>
        patchLast(m, (x) => ({ ...x, text: x.text + token, pending: false })),
      );
    });

    es.addEventListener("done", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as { citations: Citation[] };
      const citedIdx = new Set((data.citations ?? []).map((c) => c.index));
      setMsgs((m) =>
        patchLast(m, (x) => ({
          ...x,
          // 保留全部检索结果，只标记哪些被回答引用了
          citations: x.citations.map((c) => ({ ...c, cited: citedIdx.has(c.index) })),
          pending: false,
        })),
      );
      es.close();
      esRef.current = null;
      setBusy(false);
    });

    es.onerror = () => {
      es.close();
      esRef.current = null;
      setBusy(false);
      setMsgs((m) =>
        patchLast(m, (x) => ({
          ...x,
          pending: false,
          text: x.text || "连接中断，请确认后端服务在运行。",
        })),
      );
    };
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-11rem)] w-full max-w-[880px] flex-col">
      <PageHeader
        eyebrow="Ask"
        title="智能问答"
        description="用自然语言问岗位数据。回答只依据检索到的 JD 片段，每条结论标注来源编号。"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5 text-2xs text-fg3">
              检索
              <select
                className="select h-7 w-auto py-0 text-2xs"
                value={topK}
                onChange={(e) => changeK(Number(e.target.value))}
                title="每次检索几条岗位作为回答依据"
              >
                {[3, 5, 8, 12, 20].map((n) => (
                  <option key={n} value={n}>
                    {n} 条
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => toggleProfile(!useProfile)}
              className={`btn btn-sm ${useProfile ? "btn-primary" : "btn-ghost"}`}
              title="开启后回答会结合你上传的简历"
            >
              <UserRound size={13} /> {useProfile ? "已结合简历" : "结合简历"}
            </button>
            {msgs.length > 0 && (
              <button className="btn btn-ghost btn-sm" onClick={reset}>
                <RotateCcw size={14} /> 新对话
              </button>
            )}
          </div>
        }
      />

      <div className="mt-6 flex-1 space-y-6">
        {msgs.length === 0 && (
          <div className="animate-rise space-y-4">
            <div className="card p-5 sm:p-6">
              <div className="flex items-center gap-2 text-[13px] font-medium text-fg">
                <Sparkles size={15} className="text-accent" />
                试试这些问题
              </div>
              <p className="mt-1 text-xs leading-[1.7] text-fg3">
                检索会同时走 BM25 和向量，再用 RRF 融合；答案里的 [1] 就是下面的岗位来源。
                右上角可以调每次检索几条（默认 8 条）。
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    className="group flex flex-col justify-between rounded-lg border border-line/70 bg-panel2/30 p-3 text-left transition-colors hover:border-accent/40 hover:bg-panel2/60"
                    onClick={() => send(ex)}
                  >
                    <span className="text-[13px] leading-snug text-fg2 group-hover:text-fg">
                      {ex}
                    </span>
                    <span className="mt-3 inline-flex items-center gap-1 text-3xs text-fg3">
                      去问 <ArrowUpRight size={11} />
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-3">
              {[
                { label: "带引用", text: "每条结论都能点回岗位原文" },
                { label: "拒答", text: "检索不到依据时明确说不知道" },
                { label: "可追溯", text: "点开引用直接看原岗位 JD" },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-lg border border-line/60 bg-panel2/20 px-3 py-2.5"
                >
                  <div className="text-2xs font-medium text-fg2">{item.label}</div>
                  <div className="mt-0.5 text-3xs leading-4 text-fg3">{item.text}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-5" role="log" aria-live="polite">
          {msgs.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-tr-md border border-accent/20 bg-accent/10 px-4 py-2.5 text-[13.5px] leading-[1.7] text-fg">
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={i} className="flex gap-3 border-b border-line/40 pb-5 last:border-0">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-accent/25 bg-accent/10 text-accent">
                  <Radar size={14} strokeWidth={2} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="mb-1.5 flex items-center gap-2">
                    <span className="text-2xs font-medium text-fg2">job-scout</span>
                    <span className="tag text-3xs">RAG</span>
                  </div>

                  {m.text ? (
                    <div className="md">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {linkifyCitations(m.text, i)}
                      </ReactMarkdown>
                      {m.pending && (
                        <span className="ml-0.5 inline-block h-4 w-[2px] animate-blink bg-accent align-middle" />
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 py-1 text-xs text-fg3">
                      <Loader2 size={13} className="animate-spin text-accent" />
                      正在检索岗位库并组织回答…
                    </div>
                  )}

                  {m.citations.length > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center gap-1.5 text-2xs text-fg3">
                        <Quote size={11} />
                        检索 {m.citations.length} 条，回答引用了{" "}
                        {m.citations.filter((c) => c.cited).length} 条
                      </div>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        {m.citations.map((c) => (
                          <Link
                            key={c.index}
                            id={`cite-${i}-${c.index}`}
                            href={`/jobs/${c.job_id}`}
                            className={`cite-card group flex scroll-mt-24 items-start gap-2 rounded-lg border px-3 py-2 transition-colors hover:border-accent/40 hover:bg-panel2/60 ${
                              c.cited
                                ? "border-accent/30 bg-accent/[0.04]"
                                : "border-line/70 bg-panel2/30"
                            }`}
                          >
                            <span
                              className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded text-3xs font-medium ${
                                c.cited
                                  ? "bg-accent/15 text-accent"
                                  : "bg-panel3/60 text-fg3"
                              }`}
                            >
                              {c.index}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="block truncate text-xs text-fg2 group-hover:text-fg">
                                {c.title}
                              </span>
                              <span className="mt-0.5 block truncate text-3xs text-fg3">
                                {c.company} · {c.district || "-"} · {c.salary || "-"}
                              </span>
                            </span>
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ),
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="sticky bottom-20 z-30 mt-6 lg:bottom-4">
        <div className="card p-2 shadow-pop">
          <div className="flex items-center gap-2">
            <input
              className="h-9 flex-1 border-0 bg-transparent px-2 text-[13.5px] text-fg outline-none placeholder:text-fg3"
              placeholder="问点什么，比如：哪些实习岗要求 RAG？"
              aria-label="输入问题"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.nativeEvent.isComposing) send(question);
              }}
            />
            {busy ? (
              <button className="btn btn-ghost btn-sm" onClick={stop}>
                <StopCircle size={14} /> 停止
              </button>
            ) : (
              <button
                className="btn btn-primary btn-sm"
                onClick={() => send(question)}
                disabled={!question.trim()}
              >
                <Send size={13} /> 发送
              </button>
            )}
          </div>
        </div>
        <div className="mt-1.5 flex items-center justify-between px-1 text-3xs text-fg3">
          <span>回答只依据已采集的 JD，不编造岗位</span>
          <span className="hidden sm:inline">Enter 发送</span>
        </div>
      </div>
    </div>
  );
}
