"use client";

import { Check, FolderCode, Loader2, ScanSearch } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import FolderPicker from "@/components/FolderPicker";
import {
  api,
  type CodeProject,
  type ReviewResult,
} from "@/lib/api";

/**
 * 项目代码：把简历里的每个项目列出来，逐个指定代码目录。
 *
 * 绑定关系靠 project_name 精确匹配，不用名字自动猜——
 * 你点哪个项目、选哪个文件夹，就是哪个。
 */
export default function CodeProjects({ projects }: { projects: string[] }) {
  const [links, setLinks] = useState<Record<string, CodeProject>>({});
  const [picking, setPicking] = useState<string | null>(null);
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [reviewBusy, setReviewBusy] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { items } = await api.codeList();
      const map: Record<string, CodeProject> = {};
      for (const it of items) map[it.project_name] = it;
      setLinks(map);
    } catch {
      setLinks({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function unlink(name: string) {
    const it = links[name];
    if (!it) return;
    await api.codeDelete(it.slug).catch(() => undefined);
    setReview(null);
    setMsg(`已取消关联：${name}`);
    await load();
  }

  async function reviewOne(name: string) {
    setReviewBusy(name);
    setMsg("");
    try {
      setReview(await api.codeReview(name));
    } catch (e) {
      setMsg(`审查失败：${String(e).slice(0, 120)}`);
    } finally {
      setReviewBusy("");
    }
  }

  return (
    <section className="card p-5">
      <div className="flex items-center gap-2">
        <FolderCode size={15} className="text-fg3" />
        <h2 className="section-title">项目代码</h2>
        <span className="text-2xs text-fg3">可选</span>
      </div>
      <p className="mt-1.5 text-xs leading-[1.7] text-fg3">
        下面是你简历里的项目。点「选择文件夹」指定它的代码目录，
        之后改写简历时会引用代码里**确实有**的技术点，也能对照审查描述准不准。
      </p>

      {msg && (
        <div className="mt-3 rounded-lg border border-accent/20 bg-accent/[0.05] px-3 py-2 text-2xs leading-[1.7] text-accent">
          {msg}
        </div>
      )}

      {projects.length === 0 ? (
        <p className="mt-4 text-2xs text-fg3">先上传简历，识别出项目后再来关联代码。</p>
      ) : (
        <ul className="mt-4 space-y-2">
          {projects.map((name) => {
            const it = links[name];
            const busy = reviewBusy === name;
            return (
              <li key={name} className="rounded-lg border border-line/60 bg-panel2/30">
                <div className="flex flex-wrap items-start justify-between gap-2 px-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="text-xs text-fg">{name}</div>
                    <div className="mt-0.5 text-3xs text-fg3">
                      {loading ? (
                        "读取中…"
                      ) : it ? (
                        <span className="text-mint">
                          已关联 · {it.file_count} 个文件 / {it.line_count} 行
                        </span>
                      ) : (
                        "还没有指定代码目录"
                      )}
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap items-center gap-1">
                    <button
                      className={`btn btn-sm ${it ? "btn-ghost" : "btn-primary"}`}
                      onClick={() => setPicking(name)}
                    >
                      <FolderCode size={12} /> {it ? "换目录" : "选择文件夹"}
                    </button>
                    {it && (
                      <>
                        <button
                          className="btn btn-quiet btn-sm"
                          onClick={() => reviewOne(name)}
                          disabled={busy}
                          title="对照代码看简历这段写得准不准"
                        >
                          {busy ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : (
                            <ScanSearch size={12} />
                          )}
                          对照审查
                        </button>
                        <button
                          className="btn btn-quiet btn-sm"
                          onClick={() => unlink(name)}
                          title="取消关联"
                        >
                          取消
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {review?.project === name && (
                  <div className="border-t border-line/60 px-3 py-3 text-xs">
                    {review.verdict && (
                      <p className="mb-2.5 leading-[1.7] text-fg2">{review.verdict}</p>
                    )}

                    {review.inaccurate.length > 0 && (
                      <div className="mb-2.5">
                        <div className="text-2xs text-amber-400">⚠ 和代码不符</div>
                        {review.inaccurate.map((x, i) => (
                          <div
                            key={i}
                            className="mt-1.5 rounded border border-amber-500/20 bg-amber-500/[0.05] px-2.5 py-2"
                          >
                            <div className="text-2xs leading-[1.7] text-fg3">
                              简历：<span className="text-fg2">{x.claim}</span>
                            </div>
                            <div className="text-2xs leading-[1.7] text-fg3">
                              代码：<span className="text-fg2">{x.reality}</span>
                            </div>
                            <div className="mt-1 text-2xs leading-[1.7] text-mint">
                              改：{x.fix}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {review.missing.length > 0 && (
                      <div className="mb-2.5">
                        <div className="text-2xs text-accent">+ 代码里有、简历没写</div>
                        {review.missing.map((x, i) => (
                          <div key={i} className="mt-1.5 pl-2 text-2xs leading-[1.7]">
                            <span className="text-fg3">代码：</span>
                            <span className="text-fg2">{x.fact}</span>
                            <div className="text-mint">可补：{x.suggest}</div>
                          </div>
                        ))}
                      </div>
                    )}

                    {review.rewrites.length > 0 && (
                      <div>
                        <div className="text-2xs text-fg3">↻ 改写建议</div>
                        {review.rewrites.map((x, i) => (
                          <div key={i} className="mt-1.5 rounded bg-panel2/60 px-2.5 py-2">
                            <div className="text-2xs leading-[1.7] text-fg3">
                              原：{x.original}
                            </div>
                            <div className="mt-0.5 text-2xs leading-[1.7] text-fg">
                              改：{x.suggested}
                            </div>
                            <div className="mt-0.5 text-3xs text-fg3">依据：{x.why}</div>
                          </div>
                        ))}
                      </div>
                    )}

                    {review.cut.length > 0 && (
                      <div className="mt-2.5">
                        <div className="text-2xs text-fg3">− 建议弱化</div>
                        {review.cut.map((x, i) => (
                          <div key={i} className="mt-1 pl-2 text-2xs text-fg3">
                            · {x}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {picking && (
        <FolderPicker
          projectName={picking}
          onClose={() => setPicking(null)}
          onDone={async (r) => {
            setPicking(null);
            setMsg(`「${picking}」已关联：${r.files} 个文件 / ${r.lines} 行`);
            await load();
          }}
        />
      )}
    </section>
  );
}
