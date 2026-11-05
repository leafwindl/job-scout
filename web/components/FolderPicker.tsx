"use client";

import {
  ArrowLeft,
  Check,
  ChevronRight,
  Folder,
  FolderOpen,
  Loader2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AiLoading } from "@/components/AiLoading";
import { api, type BrowseResult } from "@/lib/api";

/**
 * 文件夹选择器：逐级进入目录，选一个作为项目代码。
 *
 * projectName 用于把「简历里的项目」和「代码目录」直接绑定——
 * 不依赖名字自动匹配，用户选中哪个就是哪个。
 */
export default function FolderPicker({
  projectName,
  onClose,
  onDone,
}: {
  projectName: string;
  onClose: () => void;
  onDone: (result: { files: number; lines: number; path: string }) => void;
}) {
  const [dir, setDir] = useState<BrowseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const goto = useCallback(async (path: string) => {
    setLoading(true);
    setErr("");
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

  async function useCurrent() {
    if (!dir?.path) return;
    setBusy(true);
    setErr("");
    try {
      const r = await api.codeScan(dir.path, projectName);
      onDone({ files: r.file_count, lines: r.line_count, path: r.path });
    } catch (e) {
      setErr(`扫描失败：${String(e).slice(0, 120)}`);
    } finally {
      setBusy(false);
    }
  }

  async function useEntry(path: string) {
    setBusy(true);
    setErr("");
    try {
      const r = await api.codeScan(path, projectName);
      onDone({ files: r.file_count, lines: r.line_count, path: r.path });
    } catch (e) {
      setErr(`扫描失败：${String(e).slice(0, 120)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 p-4 backdrop-blur-sm">
      <div className="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-line bg-panel shadow-pop">
        <div className="flex items-center justify-between border-b border-line/60 px-4 py-3">
          <div className="min-w-0">
            <div className="text-sm font-medium text-fg">
              给「<span className="text-accent">{projectName}</span>」选代码目录
            </div>
            <div className="mt-0.5 text-2xs text-fg3">
              进入项目的文件夹，点「用这个目录」；或者直接点子目录右边的 ↗
            </div>
          </div>
          <button className="btn btn-quiet btn-sm shrink-0" onClick={onClose}>
            <X size={13} />
          </button>
        </div>

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

        {dir?.note && (
          <div className="border-b border-line/60 bg-accent/[0.04] px-4 py-1.5 text-2xs leading-[1.7] text-fg3">
            {dir.note}
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-auto px-2 py-2">
          {busy ? (
            // 扫描会跑 ReAct 读代码（约 50 秒），分阶段提示比分阶段转圈有用
            <div className="px-3 py-4">
              <AiLoading
                title={`正在读「${projectName}」的代码`}
                stages={[
                  "扫描目录结构",
                  "挑选核心文件",
                  "阅读主要模块",
                  "生成技术画像",
                ]}
                estimatedSeconds={50}
                hint="模型会自己决定读哪些文件，产出「技术偏向 + 项目结构 + 核心实现」，用来写简历。"
              />
            </div>
          ) : loading && !dir ? (
            <div className="flex items-center justify-center py-10 text-xs text-fg3">
              <Loader2 size={14} className="mr-2 animate-spin" /> 读取目录…
            </div>
          ) : (
            <ul className="space-y-0.5">
              {(dir?.dirs ?? []).map((d) => (
                <li key={d.path} className="flex items-center gap-1">
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
                      title="就用这个目录"
                      onClick={() => useEntry(d.path)}
                      disabled={busy}
                    >
                      <Check size={12} />
                    </button>
                  )}
                </li>
              ))}
              {dir && dir.dirs.length === 0 && !loading && (
                <li className="px-3 py-8 text-center text-2xs text-fg3">
                  这个目录没有子文件夹
                </li>
              )}
            </ul>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line/60 px-4 py-3">
          <span className="min-w-0 flex-1 truncate text-2xs text-fg3">{err}</span>
          <div className="flex shrink-0 gap-2">
            <button className="btn btn-ghost btn-sm" onClick={onClose}>
              取消
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={useCurrent}
              disabled={!dir?.path || busy}
            >
              {busy ? (
                <>
                  <Loader2 size={13} className="animate-spin" /> 扫描中
                </>
              ) : (
                <>
                  <FolderOpen size={13} /> 用这个目录
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
