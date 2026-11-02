"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, type Profile } from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setProfile(await api.profile());
    } catch {
      setProfile(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(file: File) {
    setUploading(true);
    setMsg("");
    try {
      const r = await api.uploadResume(file);
      setMsg(`解析完成：${r.skills} 项技能，${r.projects} 个项目`);
      await load();
    } catch (e) {
      setMsg(`上传失败：${String(e)}`);
    } finally {
      setUploading(false);
    }
  }

  const p = profile;
  const hasProfile = Boolean(p?.uploaded);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">我的简历</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          上传 PDF 简历后，系统会提取你的技能和项目经历，用来给岗位打分、生成打招呼消息。
          文件只存在本地，不会上传到任何第三方。
        </p>
      </div>

      <div
        className="card p-6"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) upload(f);
        }}
      >
        <div className="flex flex-wrap items-center gap-4">
          <button
            className="btn btn-primary"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "解析中…" : hasProfile ? "重新上传 PDF" : "上传 PDF 简历"}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
            }}
          />
          <span className="text-sm text-slate-500">也可以把 PDF 拖到这个框里</span>
        </div>
        {msg && <div className="mt-3 text-sm text-accent">{msg}</div>}

        {hasProfile && (
          <div className="mt-4 border-t border-line pt-4 text-sm">
            <div className="text-slate-300">
              {p?.name || "（未识别姓名）"}
              {p?.target ? ` · ${p.target}` : ""}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              来源文件：{p?.source_file || "—"}
            </div>
          </div>
        )}
      </div>

      {!hasProfile && (
        <div className="card border-amber-600/40 p-5 text-sm text-amber-400">
          还没有简历。上传后，「岗位详情」页才会出现匹配分析和打招呼生成。
        </div>
      )}

      {hasProfile && p && (
        <>
          <section className="card p-6">
            <h2 className="text-sm font-medium text-slate-300">
              技能 <span className="text-slate-500">（{p.skills?.length ?? 0}）</span>
            </h2>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(p.skills ?? []).map((s) => (
                <span key={s} className="tag">
                  {s}
                </span>
              ))}
            </div>
          </section>

          <section className="card p-6">
            <h2 className="text-sm font-medium text-slate-300">
              项目经历 <span className="text-slate-500">（{p.projects?.length ?? 0}）</span>
            </h2>
            <div className="mt-4 space-y-5">
              {(p.projects ?? []).map((proj, i) => (
                <div key={i}>
                  <div className="text-sm text-slate-200">
                    {proj.name}
                    {proj.period && (
                      <span className="ml-2 text-xs text-slate-500">{proj.period}</span>
                    )}
                  </div>
                  {proj.tech && proj.tech.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {proj.tech.map((t) => (
                        <span key={t} className="tag text-[11px]">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-400">
                    {(proj.bullets ?? []).map((b, j) => (
                      <li key={j}>{b}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          {(p.experience?.length ?? 0) > 0 && (
            <section className="card p-6">
              <h2 className="text-sm font-medium text-slate-300">实习经历</h2>
              <div className="mt-3 space-y-4">
                {(p.experience ?? []).map((exp, i) => (
                  <div key={i}>
                    <div className="text-sm text-slate-200">
                      {exp.company} {exp.role}
                    </div>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-400">
                      {(exp.bullets ?? []).map((b, j) => (
                        <li key={j}>{b}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>
          )}

          {(p.education?.length ?? 0) > 0 && (
            <section className="card p-6">
              <h2 className="text-sm font-medium text-slate-300">教育背景</h2>
              <div className="mt-3 space-y-1 text-sm text-slate-300">
                {(p.education ?? []).map((e, i) => (
                  <div key={i}>
                    {e.school} · {e.major} · {e.degree}
                    {e.time && <span className="ml-2 text-xs text-slate-500">{e.time}</span>}
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
