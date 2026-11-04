"use client";

import { Check, FolderCode, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import FolderPicker from "@/components/FolderPicker";
import { api, type CodeProject } from "@/lib/api";

/**
 * 简历里某个项目的代码关联状态。
 *
 * 用户手动指定目录，不做名字自动匹配——这样「简历项目 → 代码目录」
 * 的绑定关系完全由你决定，不会张冠李戴。
 */
export default function ProjectCodeLink({ projectName }: { projectName: string }) {
  const [linked, setLinked] = useState<CodeProject | null>(null);
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { items } = await api.codeList();
      // 后端按 project_name 存，这里精确匹配
      setLinked(items.find((x) => x.project_name === projectName) ?? null);
    } catch {
      setLinked(null);
    } finally {
      setLoading(false);
    }
  }, [projectName]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <span className="inline-flex items-center gap-1 text-3xs text-fg3">
        <Loader2 size={10} className="animate-spin" />
      </span>
    );
  }

  if (linked) {
    return (
      <span className="inline-flex items-center gap-1.5 text-3xs">
        <span className="inline-flex items-center gap-1 rounded border border-mint/25 bg-mint/[0.08] px-1.5 py-0.5 text-mint">
          <Check size={9} /> 已关联 {linked.file_count} 文件
        </span>
        <button
          className="text-fg3 underline-offset-2 hover:text-fg hover:underline"
          onClick={() => setOpen(true)}
        >
          改
        </button>
        {open && (
          <FolderPicker
            projectName={projectName}
            onClose={() => setOpen(false)}
            onDone={async (r) => {
              setOpen(false);
              setMsg(`已关联：${r.files} 个文件 / ${r.lines} 行`);
              await load();
            }}
          />
        )}
      </span>
    );
  }

  return (
    <>
      <button
        className="inline-flex items-center gap-1 rounded border border-line px-1.5 py-0.5 text-3xs text-fg3 transition-colors hover:border-accent/40 hover:text-accent"
        onClick={() => setOpen(true)}
        title="指定这个项目的代码目录，改写简历时会引用代码实况"
      >
        <FolderCode size={9} /> 关联代码
      </button>
      {msg && <span className="ml-1.5 text-3xs text-accent">{msg}</span>}
      {open && (
        <FolderPicker
          projectName={projectName}
          onClose={() => setOpen(false)}
          onDone={async (r) => {
            setOpen(false);
            setMsg(`已关联：${r.files} 个文件 / ${r.lines} 行`);
            await load();
          }}
        />
      )}
    </>
  );
}
