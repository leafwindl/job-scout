"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BadgeCheck,
  Briefcase,
  Check,
  Circle,
  FileText,
  FolderCode,
  GraduationCap,
  Loader2,
  Sparkles,
  Upload,
  UserRound,
} from "lucide-react";

import CodeProjects from "@/components/CodeProjects";
import PageHeader from "@/components/PageHeader";
import ProjectCodeLink from "@/components/ProjectCodeLink";
import { ProgressBar, SectionHeader, Stat } from "@/components/ui";
import { api, type Profile } from "@/lib/api";

type UploadMsg = { type: "ok" | "err"; text: string } | null;

function Completeness({ profile }: { profile: Profile }) {
  const items = [
    { label: "技能标签", done: (profile.skills?.length ?? 0) >= 5, hint: `${profile.skills?.length ?? 0} 项` },
    { label: "项目经历", done: (profile.projects?.length ?? 0) >= 2, hint: `${profile.projects?.length ?? 0} 个` },
    { label: "实习经历", done: (profile.experience?.length ?? 0) >= 1, hint: `${profile.experience?.length ?? 0} 段` },
    { label: "教育背景", done: (profile.education?.length ?? 0) >= 1, hint: `${profile.education?.length ?? 0} 条` },
  ];
  const done = items.filter((i) => i.done).length;
  const pct = Math.round((done / items.length) * 100);

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <SectionHeader title="简历完整度" />
        <span className="text-2xs tabular-nums text-fg3">
          {done}/{items.length}
        </span>
      </div>
      <div className="mt-3">
        <ProgressBar value={pct} tone={done === items.length ? "mint" : "accent"} />
      </div>
      <ul className="mt-3 space-y-1.5">
        {items.map((item) => (
          <li key={item.label} className="flex items-center gap-2 text-2xs">
            {item.done ? (
              <Check size={12} className="text-mint" strokeWidth={2.4} />
            ) : (
              <Circle size={12} className="text-fg3" strokeWidth={2} />
            )}
            <span className={item.done ? "text-fg2" : "text-fg3"}>{item.label}</span>
            <span className="ml-auto tabular-nums text-fg3">{item.hint}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-3xs leading-4 text-fg3">
        技能和项目越具体，匹配分析和招呼语越准。
      </p>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<UploadMsg>(null);
  const [drag, setDrag] = useState(false);
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
    if (uploading) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setMsg({ type: "err", text: "只支持 PDF 文件，请重新选择。" });
      return;
    }
    setUploading(true);
    setMsg(null);
    try {
      const r = await api.uploadResume(file);
      setMsg({
        type: "ok",
        text: `解析完成：${r.skills} 项技能，${r.projects} 个项目。`,
      });
      await load();
    } catch (e) {
      setMsg({ type: "err", text: `上传失败：${String(e)}` });
    } finally {
      setUploading(false);
    }
  }

  const p = profile;
  const hasProfile = Boolean(p?.uploaded);
  const skillCount = p?.skills?.length ?? 0;
  const projectCount = p?.projects?.length ?? 0;
  const experienceCount = p?.experience?.length ?? 0;
  const educationCount = p?.education?.length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Profile"
        title="我的简历"
        description="上传 PDF 后自动提取技能与项目经历，用于岗位匹配、招呼语和简历改写。文件只存在本地。"
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <a href="#project-code" className="btn btn-ghost">
              <FolderCode size={15} /> 项目代码
            </a>
            {hasProfile && (
              <Link href="/prep" className="btn btn-ghost">
                看该补什么 <ArrowRight size={15} />
              </Link>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
        <div className="order-2 space-y-5 lg:order-1">
          {!hasProfile ? (
            <section className="card px-5 py-10 text-center sm:px-8">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-panel2 text-fg3">
                <FileText size={20} strokeWidth={1.6} />
              </div>
              <h3 className="mt-3 text-[14px] font-medium text-fg">还没有解析过简历</h3>
              <p className="mx-auto mt-1.5 max-w-md text-xs leading-[1.7] text-fg3">
                上传一份 PDF 简历，右侧的解析结果会出现在这里：技能、项目、实习和教育。
              </p>
              <div className="mx-auto mt-6 max-w-md space-y-2 text-left">
                {[
                  "提取技能关键词，用于岗位匹配打分",
                  "把项目经历整理成结构化条目，方便逐岗改写",
                  "生成打招呼消息时引用你的真实项目",
                ].map((line, i) => (
                  <div
                    key={line}
                    className="flex items-center gap-3 rounded-lg border border-line/60 bg-panel2/30 px-3 py-2.5"
                  >
                    <span className="flex h-5 w-5 items-center justify-center rounded-full border border-line text-3xs text-fg3">
                      {i + 1}
                    </span>
                    <span className="text-xs text-fg2">{line}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : (
            p && (
              <>
                <section className="animate-rise card p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-accent/25 bg-accent/10 text-base font-medium text-accent">
                        {p.name?.slice(0, 1) || <UserRound size={18} />}
                      </span>
                      <div className="min-w-0">
                        <h2 className="truncate text-[15px] font-medium text-fg">
                          {p.name || "未识别姓名"}
                        </h2>
                        <p className="mt-0.5 truncate text-xs text-fg3">
                          {p.target || "未填写求职方向"}
                        </p>
                      </div>
                    </div>
                    <span className="tag tag-mint">
                      <BadgeCheck size={11} /> 已解析
                    </span>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-4 border-t border-line/60 pt-4 sm:grid-cols-4">
                    <Stat label="技能" value={skillCount} unit="项" />
                    <Stat label="项目" value={projectCount} unit="个" />
                    <Stat label="实习" value={experienceCount} unit="段" />
                    <Stat label="教育" value={educationCount} unit="条" />
                  </div>

                  {p.education?.[0] && (
                    <div className="mt-4 flex items-center gap-2 border-t border-line/60 pt-3 text-2xs text-fg3">
                      <GraduationCap size={13} className="shrink-0" />
                      <span className="truncate">
                        {[p.education[0].school, p.education[0].major, p.education[0].degree]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                      {p.education[0].time && (
                        <span className="ml-auto shrink-0 tabular-nums">
                          {p.education[0].time}
                        </span>
                      )}
                    </div>
                  )}
                </section>

                <section className="card p-5">
                  <SectionHeader title="技能标签" hint={`${skillCount} 项`} />
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {(p.skills ?? []).map((s) => (
                      <span key={s} className="tag border-line bg-panel2/60 text-fg2">
                        {s}
                      </span>
                    ))}
                    {skillCount === 0 && (
                      <span className="text-xs text-fg3">没有提取到技能关键词。</span>
                    )}
                  </div>
                </section>

                <section className="card p-5">
                  <SectionHeader
                    title="项目经历"
                    hint={`${projectCount} 个`}
                    icon={Sparkles}
                  />
                  <ol className="relative mt-4 space-y-5 before:absolute before:bottom-2 before:left-[5px] before:top-2 before:w-px before:bg-line">
                    {(p.projects ?? []).map((proj, i) => (
                      <li key={i} className="relative pl-6">
                        <span className="absolute left-0 top-[7px] h-[11px] w-[11px] rounded-full border-2 border-panel bg-accent/70" />
                        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-[13.5px] font-medium text-fg">
                              {proj.name || `项目 ${i + 1}`}
                            </h3>
                            {proj.name && <ProjectCodeLink projectName={proj.name} />}
                          </div>
                          {proj.period && (
                            <span className="text-2xs tabular-nums text-fg3">{proj.period}</span>
                          )}
                        </div>
                        {proj.tech && proj.tech.length > 0 && (
                          <div className="mt-1.5 flex flex-wrap gap-1">
                            {proj.tech.map((t) => (
                              <span key={t} className="tag">
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                        <ul className="mt-2 space-y-1.5">
                          {(proj.bullets ?? []).map((b, j) => (
                            <li
                              key={j}
                              className="flex gap-2 text-[13px] leading-[1.7] text-fg2"
                            >
                              <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-fg3" />
                              <span>{b}</span>
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                    {projectCount === 0 && (
                      <li className="pl-6 text-xs text-fg3">没有识别到项目经历。</li>
                    )}
                  </ol>
                </section>

                {experienceCount > 0 && (
                  <section className="card p-5">
                    <SectionHeader
                      title="实习经历"
                      hint={`${experienceCount} 段`}
                      icon={Briefcase}
                    />
                    <div className="mt-3 space-y-5">
                      {(p.experience ?? []).map((exp, i) => (
                        <div key={i} className="flex gap-3">
                          <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-mint/20 bg-mint/[0.06] text-mint">
                            <Briefcase size={13} />
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-baseline justify-between gap-2">
                              <h3 className="text-[13.5px] font-medium text-fg">
                                {exp.company}{" "}
                                <span className="font-normal text-fg2">{exp.role}</span>
                              </h3>
                              {exp.period && (
                                <span className="text-2xs tabular-nums text-fg3">
                                  {exp.period}
                                </span>
                              )}
                            </div>
                            <ul className="mt-1.5 space-y-1">
                              {(exp.bullets ?? []).map((b, j) => (
                                <li
                                  key={j}
                                  className="flex gap-2 text-[13px] leading-[1.7] text-fg2"
                                >
                                  <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-fg3" />
                                  <span>{b}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {educationCount > 0 && (
                  <section className="card p-5">
                    <SectionHeader
                      title="教育背景"
                      hint={`${educationCount} 条`}
                      icon={GraduationCap}
                    />
                    <div className="mt-3 space-y-2">
                      {(p.education ?? []).map((e, i) => (
                        <div
                          key={i}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line/60 bg-panel2/30 px-3 py-2.5"
                        >
                          <div className="min-w-0">
                            <div className="text-[13px] text-fg">{e.school}</div>
                            <div className="mt-0.5 text-2xs text-fg3">
                              {[e.major, e.degree].filter(Boolean).join(" · ")}
                            </div>
                          </div>
                          {e.time && (
                            <span className="text-2xs tabular-nums text-fg3">{e.time}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </>
            )
          )}
        </div>

        <aside className="order-1 space-y-4 lg:order-2 lg:sticky lg:top-6">
          <div
            className={`card p-4 transition-colors ${
              drag ? "border-accent/60 bg-accent/[0.04]" : ""
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              const f = e.dataTransfer.files?.[0];
              if (f) upload(f);
            }}
          >
            <div className="flex flex-col items-center rounded-lg border border-dashed border-line/80 px-4 py-6 text-center">
              <span
                className={`flex h-10 w-10 items-center justify-center rounded-xl border text-[15px] ${
                  drag
                    ? "border-accent/40 bg-accent/10 text-accent"
                    : "border-line bg-panel2 text-fg3"
                }`}
              >
                {uploading ? (
                  <Loader2 size={17} className="animate-spin" />
                ) : (
                  <Upload size={17} strokeWidth={1.8} />
                )}
              </span>
              <div className="mt-3 text-[13px] font-medium text-fg">
                {uploading ? "正在解析…" : hasProfile ? "更新简历" : "上传 PDF 简历"}
              </div>
              <p className="mt-1 text-2xs leading-4 text-fg3">
                拖拽 PDF 到这里，或点击选择文件
              </p>
              <button
                type="button"
                className="btn btn-primary btn-sm mt-3 w-full"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? (
                  <>
                    <Loader2 size={13} className="animate-spin" /> 解析中
                  </>
                ) : (
                  <>
                    <Upload size={13} /> 选择 PDF
                  </>
                )}
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf,.pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload(f);
                  e.target.value = "";
                }}
              />
              <p className="mt-2 text-3xs text-fg3">文件只存在本地，不会上传第三方</p>
            </div>

            {msg && (
              <div
                className={`mt-3 flex items-start gap-1.5 rounded-md border px-2.5 py-2 text-2xs leading-4 ${
                  msg.type === "ok"
                    ? "border-mint/25 bg-mint/[0.06] text-mint"
                    : "border-rose-500/25 bg-rose-500/[0.06] text-rose-300"
                }`}
                role="status"
              >
                <span>{msg.text}</span>
              </div>
            )}

            {hasProfile && p?.source_file && (
              <div className="mt-3 flex items-center gap-1.5 border-t border-line/60 pt-3 text-3xs text-fg3">
                <FileText size={11} />
                <span className="truncate">{p.source_file}</span>
              </div>
            )}
          </div>

          {hasProfile && p && <Completeness profile={p} />}

          <div className="card px-4 py-3.5">
            <div className="text-2xs text-fg3">小提示</div>
            <p className="mt-1.5 text-2xs leading-[1.7] text-fg3">
              改完简历后重新上传，岗位详情页的匹配分析会跟着更新。项目 bullet 写清「做了什么 + 结果」比堆技术名词更有用。
            </p>
          </div>
        </aside>
      </div>

      {/* 项目代码：给简历改写提供事实依据 */}
      <div id="project-code" className="mt-6 scroll-mt-24">
        <CodeProjects />
      </div>
    </div>
  );
}
