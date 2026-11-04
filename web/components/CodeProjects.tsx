"use client";

import {
  ArrowLeft,
  Check,
  ChevronRight,
  Folder,
  FolderCode,
  FolderOpen,
  Loader2,
  Plus,
  ScanSearch,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  api,
  type BrowseResult,
  type CodeProject,
  type ProjectCandidate,
  type ReviewResult,
} from "@/lib/api";

/** 项目代码：选文件夹 → 自动发现子项目 → 批量关联。 */
export default function CodeProjects() {
  const [items, setItems] = useState<CodeProject[]>([]);
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [reviewBusy, setReviewBusy] = useState("");

  const load = useCallback(async () => {
    try {
      setItems((await api.codeList()).items);
    } catch {
      setItems([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function reviewOne(project: string) {
    setReviewBusy(project);
    setMsg("");
    try {
      setReview(await api.codeReview(project));
    } catch (e) {
      setMsg(`审查失败：${String(e)}`);
    } finally {
      setReviewBusy("");
    }
  }

  async function remove(slug: string) {
    await api.codeDelete(slug).catch(() => undefined);
    await load();
  }

  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <FolderCode size={15} className="text-fg3" />
          <h2 className="section-title">项目代码</h2>
          <span className="text-2xs text-fg3">可选</span>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setOpen(true)}>
          <Plus size={13} /> 添加项目
        </button>
      </div>

      <p className="mt-1.5 text-xs leading-[1.7] text-fg3">
        选一个文件夹，系统会自动发现里面的项目（有 package.json / pyproject.toml / .git
        的目录），也可以只选某个项目目录。扫描后改写简历时会引用代码里**确实有**的技术点。
      </p>

      {msg && (
        <div className="mt-3 rounded-lg border border-accent/20 bg-accent/[0.05] px-3 py-2 text-2xs leading-[1.7] text-accent">
          {msg}
        </div>
      )}

      {items.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {items.map((it) => (
            <li key={it.slug} className="rounded-lg border border-line/60 bg-panel2/30">
              <div className="flex items-start justify-between gap-3 px-3 py-2.5">
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-fg">{it.project_name}</div>
                  <div className="mt-0.5 truncate text-3xs text-fg3">
                    {it.file_count} 个文件 · {it.line_count} 行 ·{" "}
                    {Object.keys(it.langs || {})
                      .slice(0, 3)
                      .join("/")}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    className="btn btn-quiet btn-sm"
                    onClick={() => reviewOne(it.project_name)}
                    disabled={reviewBusy === it.project_name}
                    title="对照代码看简历这段写得准不准"
                  >
                    {reviewBusy === it.project_name ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <ScanSearch size={12} />
                    )}
                    对照审查
                  </button>
                  <button
                    className="btn btn-quiet btn-sm"
                    onClick={() => remove(it.slug)}
                    title="删除"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>

              {review?.project === it.project_name && (
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
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-2xs text-fg3">还没有关联项目。</p>
      )}

      {open && (
        <FolderPicker
          onClose={() => setOpen(false)}
          onDone={async (n, names) => {
            setOpen(false);
            setMsg(`已关联 ${n} 个项目：${names.join("、")}`);
            await load();
          }}
        />
      )}
    </section>
  );
}

/** 文件夹选择器：逐级进入目录，选定后自动发现子项目。 */
function FolderPicker({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: (count: number, names: string[]) => void;
}) {
  const [dir, setDir] = useState<BrowseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [candidates, setCandidates] = useState<ProjectCandidate[] | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const goto = useCallback(async (path: string) => {
    setLoading(true);
    setErr("");
    setCandidates(null);
    setPicked(new Set());
    try {
      setDir(await api.codeBrowse(path));
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    goto("");
  }, [goto]);

  async function discover() {
    if (!dir?.path) return;
    setLoading(true);
    setErr("");
    try {
      const r = await api.codeDiscover(dir.path);
      setCandidates(r.items);
      setPicked(new Set(r.items.map((x) => x.name)));
      if (!r.items.length) setErr("这个目录下没发现项目，可以再往里进一层");
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function scanSelected() {
    if (!dir?.path || !picked.size) return;
    setBusy(true);
    setErr("");
    try {
      const r = await api.codeScanMany(dir.path, Array.from(picked));
      const ok = r.items.filter((x) => x.ok);
      if (ok.length) {
        onDone(ok.length, ok.map((x) => x.name));
      } else {
        setErr("扫描失败，检查这些目录里有没有源码文件");
      }
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  function toggle(name: string) {
    const next = new Set(picked);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setPicked(next);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-4 backdrop-blur-sm">
      <div className="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-line bg-panel shadow-pop">
        {/* 头部 */}
        <div className="flex items-center justify-between border-b border-line/60 px-4 py-3">
          <div className="flex items-center gap-2">
            <FolderOpen size={15} className="text-accent" />
            <span className="text-sm font-medium text-fg">选择项目文件夹</span>
          </div>
          <button className="btn btn-quiet btn-sm" onClick={onClose}>
            <X size={13} />
          </button>
        </div>

        {/* 路径栏 */}
        <div className="flex items-center gap-2 border-b border-line/60 px-4 py-2">
          <button
            className="btn btn-quiet btn-sm"
            onClick={() => dir?.parent && goto(dir.parent)}
            disabled={!dir?.parent}
            title="上一级"
          >
            <ArrowLeft size={12} />
          </button>
          <code className="min-w-0 flex-1 truncate rounded bg-panel2/60 px-2 py-1 text-2xs text-fg2">
            {dir?.path || "（选择盘符）"}
          </code>
        </div>

        {/* 目录列表 */}
        <div className="min-h-0 flex-1 overflow-auto px-2 py-2">
          {loading && !dir ? (
            <div className="flex items-center justify-center py-10 text-xs text-fg3">
              <Loader2 size={14} className="mr-2 animate-spin" /> 读取目录…
            </div>
          ) : (
            <ul className="space-y-0.5">
              {(dir?.dirs ?? []).map((d) => (
                <li key={d.path}>
                  <div className="flex items-center gap-1">
                    <button
                      className="group flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-panel2/60"
                      onClick={() => goto(d.path)}
                    >
                      <Folder
                        size={13}
                        className={d.is_project ? "shrink-0 text-accent" : "shrink-0 text-fg3"}
                      />
                      <span className="min-w-0 flex-1 truncate text-xs text-fg2 group-hover:text-fg">
                        {d.name}
                      </span>
                      {d.is_project && <span className="tag tag-accent shrink-0">项目</span>}
                      <ChevronRight size={12} className="shrink-0 text-fg3" />
                    </button>
                    {d.is_project && (
                      <button
                        className="btn btn-quiet btn-sm shrink-0"
                        title="直接加这个项目"
                        onClick={async () => {
                          setBusy(true);
                          try {
                            const r = await api.codeScanMany(d.path.replace(/\\[^\\]+$/, ""), [
                              d.name,
                            ]);
                            const ok = r.items.find((x) => x.ok);
                            if (ok) onDone(1, [ok.name ?? d.name]);
                            else setErr("扫描失败：这个目录里没有源码");
                          } catch (e) {
                            setErr(String(e));
                          } finally {
                            setBusy(false);
                          }
                        }}
                        disabled={busy}
                      >
                        <Plus size={12} />
                      </button>
                    )}
                  </div>
                </li>
              ))}
              {dir && dir.dirs.length === 0 && !loading && (
                <li className="px-3 py-8 text-center text-2xs text-fg3">这个目录没有子文件夹</li>
              )}
            </ul>
          )}

          {/* 发现结果 */}
          {candidates && candidates.length > 0 && (
            <div className="mt-3 rounded-lg border border-accent/20 bg-accent/[0.04] p-3">
              <div className="flex items-center justify-between">
                <span className="text-2xs text-accent">
                  在当前目录发现 {candidates.length} 个项目
                </span>
                <button
                  className="text-2xs text-fg3 hover:text-fg"
                  onClick={() =>
                    setPicked(
                      picked.size === candidates.length
                        ? new Set()
                        : new Set(candidates.map((x) => x.name)),
                    )
                  }
                >
                  {picked.size === candidates.length ? "全不选" : "全选"}
                </button>
              </div>
              <ul className="mt-2 space-y-1">
                {candidates.map((c) => (
                  <li key={c.name}>
                    <label className="flex cursor-pointer items-center gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={picked.has(c.name)}
                        onChange={() => toggle(c.name)}
                        className="h-3.5 w-3.5 accent-[#4f8cff]"
                      />
                      <span className="text-fg2">{c.name}</span>
                      <span className="truncate text-2xs text-fg3">
                        {c.markers.slice(0, 3).join(" / ")}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* 底部 */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line/60 px-4 py-3">
          <span className="text-2xs text-fg3">
            {err || (candidates ? `已选 ${picked.size} 个` : "进入包含项目的文件夹，再点「发现项目」")}
          </span>
          <div className="flex gap-2">
            <button
              className="btn btn-ghost btn-sm"
              onClick={discover}
              disabled={!dir?.path || loading}
            >
              <FolderCode size={13} /> 发现项目
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={scanSelected}
              disabled={!picked.size || busy}
            >
              {busy ? (
                <>
                  <Loader2 size={13} className="animate-spin" /> 扫描中
                </>
              ) : (
                <>
                  <Check size={13} /> 添加 {picked.size || ""} 个
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
