/** API 客户端与类型定义。 */

// 服务端组件（容器内）要走 compose 服务名，浏览器要走 localhost
const SERVER_BASE =
  process.env.API_BASE_INTERNAL ??
  process.env.NEXT_PUBLIC_API_BASE ??
  "http://127.0.0.1:8001";

// 浏览器端地址（构建期注入）
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8001";

function base(): string {
  return typeof window === "undefined" ? SERVER_BASE : API_BASE;
}

export type SearchHit = {
  job_id: string;
  title: string;
  company: string;
  salary: string;
  district: string;
  url: string;
  score: number;
  skills: string[];
  category: string;
};

export type Citation = {
  index: number;
  job_id: string;
  title: string;
  company: string;
  district: string;
  salary: string;
  url: string;
  /** 前端标记：本条是否被回答正文引用 */
  cited?: boolean;
};

export type AskResponse = {
  answer: string;
  mode: string;
  citations: Citation[];
  docs_count: number;
};

export type JobItem = {
  job_id: string;
  title: string;
  company: string;
  salary: string;
  city: string;
  district: string;
  experience: string;
  category: string;
  has_jd: boolean;
  url: string;
  skills: string[];
};

export type JobListResponse = {
  total: number;
  page: number;
  size: number;
  items: JobItem[];
};

export type JobDetail = JobItem & {
  description: string;
};

export type CollectStatus = {
  state: "idle" | "running" | "done" | "stalled";
  total: number;
  with_jd: number;
  jd_pending: number;
  elapsed: number;
  done_at: number;
  message: string;
};

export type CollectStart = {
  url: string;
  started_at: number;
  city_code: string;
  keyword: string;
  city: string;
  intern?: boolean;
};

/** 采集开关：和油猴脚本共用，存在 data/collect_config.json */
export type CollectConfig = {
  only_intern: boolean;
  only_relevant: boolean;
  auto_stop: boolean;
  auto_push: boolean;
  target: number;
};

export type Health = {
  ok: boolean;
  docs: number;
  has_llm: boolean;
  mode: string;
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${base()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${base()}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export type ProfileProject = {
  name?: string;
  period?: string;
  tech?: string[];
  bullets?: string[];
};

export type ProfileExperience = {
  company?: string;
  role?: string;
  period?: string;
  bullets?: string[];
};

export type Profile = {
  uploaded: boolean;
  name?: string;
  target?: string;
  education?: { school?: string; major?: string; degree?: string; time?: string }[];
  skills?: string[];
  projects?: ProfileProject[];
  experience?: ProfileExperience[];
  raw_text?: string;
  source_file?: string;
};

export type MatchResult = {
  job_id: string;
  title: string;
  company: string;
  score: number;
  verdict: string;
  matched: string[];
  missing: string[];
  reason: string;
};

export type GreetResult = {
  job_id: string;
  title: string;
  company: string;
  greeting: string;
  chars: number;
  match: Omit<MatchResult, "job_id" | "title" | "company">;
};

export type RewriteResult = {
  job_id: string;
  title: string;
  company: string;
  summary: string;
  reorder: string[];
  rewrites: { project?: string; original?: string; suggested?: string; why?: string }[];
  add: string[];
  cut: string[];
  /** 这次改写是否用上了项目代码摘要 */
  used_code?: boolean;
};

export type CodeProject = {
  slug: string;
  project_name: string;
  name: string;
  path: string;
  file_count: number;
  line_count: number;
  langs: Record<string, number>;
  deps: string[];
  scanned_at: number;
};

export type CodeScanResult = CodeProject & {
  routes: string[];
  summary: string;
};

export type BrowseEntry = {
  name: string;
  path: string;
  is_project: boolean;
};

export type BrowseResult = {
  path: string;
  parent: string | null;
  dirs: BrowseEntry[];
  at_root?: boolean;
  error?: string;
};

export type ProjectCandidate = {
  name: string;
  path: string;
  markers: string[];
  code_files: number;
};

export type ScanManyResult = {
  total: number;
  ok_count: number;
  items: {
    name: string;
    ok: boolean;
    slug?: string;
    file_count?: number;
    line_count?: number;
    error?: string;
  }[];
};

/** 对照代码审查简历里的项目描述 */
export type ReviewResult = {
  project: string;
  verdict: string;
  inaccurate: { claim: string; reality: string; fix: string }[];
  missing: { fact: string; suggest: string }[];
  rewrites: { original: string; suggested: string; why: string }[];
  cut: string[];
};

export type CompanyProfile = {
  company: string;
  job_count: number;
  districts: string[];
  salary: string;
  skills: { name: string; count: number }[];
  signals: Record<string, number>;
  jobs: { job_id: string; title: string; salary: string }[];
  business?: string;
  tech_style?: string;
  team?: string;
  person_fit?: string;
  interview_focus?: string[];
  verdict?: string;
};

export type PrepResult = {
  scope: string;
  demand: { skill: string; jobs: number; ratio: number }[];
  have: string[];
  missing: { skill: string; jobs: number }[];
  overview?: string;
  learn?: { skill?: string; why?: string; how?: string }[];
  leverage?: string[];
  skip?: string[];
};

export const api = {
  health: () => get<Health>("/health"),
  search: (query: string, k = 10) => post<{ total: number; hits: SearchHit[] }>("/search", { query, k }),
  ask: (question: string, k = 5) => post<AskResponse>("/ask", { question, k }),
  jobs: (params: { keyword?: string; category?: string; district?: string; page?: number; size?: number }) => {
    const q = new URLSearchParams();
    if (params.keyword) q.set("keyword", params.keyword);
    if (params.category) q.set("category", params.category);
    if (params.district) q.set("district", params.district);
    q.set("page", String(params.page ?? 1));
    q.set("size", String(params.size ?? 20));
    return get<JobListResponse>(`/jobs?${q.toString()}`);
  },
  job: (id: string) => get<JobDetail>(`/jobs/${id}`),
  collectStart: (keyword: string, city: string, intern = true) =>
    post<CollectStart>("/collect/start", { keyword, city, intern }),
  collectStatus: () => get<CollectStatus>("/collect/status"),
  collectReset: () => post<{ ok: boolean }>("/collect/reset", {}),
  collectConfig: () => get<{ config: CollectConfig; defaults: CollectConfig }>("/collect/config"),
  setCollectConfig: (patch: Partial<CollectConfig>) =>
    post<{ config: CollectConfig }>("/collect/config", patch),

  // ---- 画像 / 匹配 / 招呼语 ----
  profile: () => get<Profile>("/profile"),
  uploadResume: async (file: File): Promise<{ ok: boolean; skills: number; projects: number }> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${base()}/profile/upload`, { method: "POST", body: fd });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
  patchProfile: (patch: Partial<Profile>) => post<Profile>("/profile", patch),
  match: (jobId: string) => post<MatchResult>(`/match/${jobId}`, {}),
  greet: (jobId: string, extra = "") => post<GreetResult>("/greet", { job_id: jobId, extra }),
  rewrite: (jobId: string, project = "") =>
    post<RewriteResult>(
      `/resume/rewrite/${jobId}${project ? `?project=${encodeURIComponent(project)}` : ""}`,
      {},
    ),
  codeList: () => get<{ items: CodeProject[] }>("/code"),
  codeScan: (path: string, projectName = "") =>
    post<CodeScanResult>("/code/scan", { path, project_name: projectName }),
  codeDelete: (slug: string) =>
    fetch(`${base()}/code/${encodeURIComponent(slug)}`, { method: "DELETE" }).then(
      (r) => r.json(),
    ),
  codeBrowse: (path = "") =>
    get<BrowseResult>(`/code/browse?path=${encodeURIComponent(path)}`),
  codeDiscover: (path: string) =>
    get<{ path: string; items: ProjectCandidate[] }>(
      `/code/discover?path=${encodeURIComponent(path)}`,
    ),
  codeScanMany: (path: string, only: string[] = []) =>
    post<ScanManyResult>("/code/scan-many", { path, only }),
  codeReview: (project: string) => post<ReviewResult>("/code/review", { project }),
  companies: (minJobs = 1) =>
    get<{ items: { company: string; jobs: number; districts: string[] }[] }>(
      `/companies?min_jobs=${minJobs}`,
    ),
  company: (name: string, deep = false) =>
    get<CompanyProfile>(`/company/${encodeURIComponent(name)}?deep=${deep}`),
  prep: (deep = false) => get<PrepResult>(`/prep?deep=${deep}`),
};
