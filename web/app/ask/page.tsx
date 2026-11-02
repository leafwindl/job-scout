"use client";

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { API_BASE, type Citation } from "@/lib/api";

type Msg = {
  role: "user" | "assistant";
  text: string;
  citations: Citation[];
  pending?: boolean;
};

/** 把回答里的 [1][2] 变成可点击锚点，跳到对应引用卡片。 */
function linkifyCitations(text: string): string {
  return text.replace(/\[(\d+)\]/g, (_m, n: string) => `[[${n}]](#cite-${n})`);
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
  const esRef = useRef<EventSource | null>(null);

  function stop() {
    esRef.current?.close();
    esRef.current = null;
    setBusy(false);
    setMsgs((m) => patchLast(m, (x) => ({ ...x, pending: false })));
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
      `${API_BASE}/ask/stream?q=${encodeURIComponent(text)}&k=5`,
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
      setMsgs((m) =>
        patchLast(m, (x) => ({ ...x, citations: data.citations ?? [], pending: false })),
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">智能问答</h1>
        <p className="mt-2 text-sm text-slate-400">
          回答只依据检索到的岗位片段，每条结论标注来源编号。
        </p>
      </div>

      <div className="space-y-4">
        {msgs.length === 0 && (
          <div className="card p-6">
            <div className="text-sm text-slate-400">试试这些问题：</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex} className="btn btn-ghost" onClick={() => send(ex)}>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        )}

        {msgs.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[80%] rounded-xl bg-accent/15 px-4 py-3 text-sm">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className="card p-5">
              <div className="md">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {linkifyCitations(m.text)}
                </ReactMarkdown>
                {m.pending && <span className="ml-1 animate-pulse text-accent">▍</span>}
              </div>

              {m.citations.length > 0 && (
                <div className="mt-4 space-y-2 border-t border-line pt-4">
                  <div className="text-xs text-slate-500">引用岗位</div>
                  {m.citations.map((c) => (
                    <a
                      key={c.index}
                      id={`cite-${c.index}`}
                      href={`/jobs/${c.job_id}`}
                      className="cite-card flex scroll-mt-24 items-start gap-3 rounded-lg border border-transparent bg-panel2 px-3 py-2 text-sm hover:bg-panel2/70"
                    >
                      <span className="mt-0.5 text-xs text-accent">[{c.index}]</span>
                      <span className="flex-1">
                        <span className="text-slate-200">{c.title}</span>
                        <span className="ml-2 text-xs text-slate-500">
                          {c.company} · {c.district || "-"} · {c.salary || "-"}
                        </span>
                      </span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          ),
        )}
      </div>

      <div className="sticky bottom-4">
        <div className="card flex gap-2 p-2">
          <input
            className="input border-0 bg-transparent focus:border-0"
            placeholder="问点什么，比如：哪些实习岗要求 RAG？"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.nativeEvent.isComposing) send(question);
            }}
          />
          {busy ? (
            <button className="btn btn-ghost whitespace-nowrap" onClick={stop}>
              停止
            </button>
          ) : (
            <button className="btn btn-primary whitespace-nowrap" onClick={() => send(question)}>
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
