"use client";

import { FolderCode, Loader2, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api, type CodeProject } from "@/lib/api";

/** 项目代码：扫描本地目录，供简历改写引用。 */
export default function CodeProjects() {
  const [items, setItems] = useState<CodeProject[]>([]);
  const [path, setPath] = useState("");
  const [projectName, setProjectName] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

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

  async function scan() {
    if (!path.trim()) return;
    setBusy(true);
    setMsg("");
    try {
      const r = await api.codeScan(path.trim(), projectName.trim());
      setMsg(
        `已扫描「${r.project_name}」：${r.file_count} 个文件 / ${r.line_count} 行`,
      );
      setPath("");
      setProjectName("");
      await load();
    } catch (e) {
      setMsg(`扫描失败：${String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function remove(slug: string) {
    await api.codeDelete(slug).catch(() => undefined);
    await load();
  }

  return (
    <section className="card p-5">
      <div className="flex items-center gap-2">
        <FolderCode size={15} className="text-fg3" />
        <h2 className="section-title">项目代码</h2>
        <span className="text-2xs text-fg3">可选</span>
      </div>
      <p className="mt-1.5 text-xs leading-[1.7] text-fg3">
        填一个本地项目目录，系统会扫描技术栈、接口、模块结构，生成摘要。
        之后改写简历时，会引用代码里**确实有**的技术点，避免只凭简历原文猜测。
      </p>

      <div className="mt-4 space-y-2">
        <input
          className="input"
          placeholder="项目路径，例如 F:\project_work\AI_Chat"
          value={path}
          onChange={(e) => setPath(e.target.value)}
        />
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input flex-1"
            placeholder="对应简历里的项目名（留空则用目录名）"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
          />
          <button className="btn btn-primary" onClick={scan} disabled={busy}>
            {busy ? (
              <>
                <Loader2 size={14} className="animate-spin" /> 扫描中
              </>
            ) : (
              <>
                <Plus size={14} /> 扫描并关联
              </>
            )}
          </button>
        </div>
      </div>

      {msg && (
        <div className="mt-3 rounded-lg border border-accent/20 bg-accent/[0.05] px-3 py-2 text-2xs leading-[1.7] text-accent">
          {msg}
        </div>
      )}

      {items.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {items.map((it) => (
            <li
              key={it.slug}
              className="flex items-start justify-between gap-3 rounded-lg border border-line/60 bg-panel2/30 px-3 py-2.5"
            >
              <div className="min-w-0">
                <div className="text-xs text-fg">{it.project_name}</div>
                <div className="mt-0.5 truncate text-3xs text-fg3">
                  {it.file_count} 个文件 · {it.line_count} 行 ·{" "}
                  {Object.keys(it.langs || {})
                    .slice(0, 3)
                    .join("/")}
                </div>
              </div>
              <button
                className="btn btn-quiet btn-sm shrink-0"
                onClick={() => remove(it.slug)}
                title="删除"
              >
                <Trash2 size={12} />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-2xs text-fg3">还没有提交项目代码。</p>
      )}
    </section>
  );
}
