"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Briefcase,
  Download,
  FileText,
  FlaskConical,
  GraduationCap,
  LayoutDashboard,
  MessagesSquare,
  Radar,
  type LucideIcon,
} from "lucide-react";

import { api, type Health, type Profile } from "@/lib/api";

type NavItem = { href: string; label: string; icon: LucideIcon };

const GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "工作台",
    items: [
      { href: "/", label: "概览", icon: LayoutDashboard },
      { href: "/jobs", label: "岗位库", icon: Briefcase },
      { href: "/prep", label: "技术准备", icon: GraduationCap },
      { href: "/ask", label: "智能问答", icon: MessagesSquare },
    ],
  },
  {
    title: "我的",
    items: [
      { href: "/profile", label: "我的简历", icon: FileText },
      { href: "/collect", label: "采集任务", icon: Download },
    ],
  },
  {
    title: "数据",
    items: [
      { href: "/dashboard", label: "数据看板", icon: BarChart3 },
      { href: "/eval", label: "检索评测", icon: FlaskConical },
    ],
  },
];

const MOBILE: NavItem[] = [
  { href: "/", label: "概览", icon: LayoutDashboard },
  { href: "/jobs", label: "岗位", icon: Briefcase },
  { href: "/ask", label: "问答", icon: MessagesSquare },
  { href: "/prep", label: "准备", icon: GraduationCap },
  { href: "/profile", label: "我的", icon: FileText },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Brand() {
  return (
    <Link href="/" className="group flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white shadow-card">
        <Radar size={17} strokeWidth={2.2} />
      </span>
      <span className="min-w-0">
        <span className="block text-[13px] font-semibold leading-4 text-fg">job-scout</span>
        <span className="block text-3xs leading-4 text-fg3">求职决策系统</span>
      </span>
    </Link>
  );
}

function ProfileBadge({ profile }: { profile: Profile | null }) {
  const ready = Boolean(profile?.uploaded);
  const initial = profile?.name?.trim().slice(0, 1) ?? "";
  return (
    <Link
      href="/profile"
      className="flex items-center gap-2.5 rounded-lg p-2 transition-colors hover:bg-white/[0.03]"
    >
      <span
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-2xs font-medium ${
          ready
            ? "border-mint/30 bg-mint/10 text-mint"
            : "border-line bg-panel2 text-fg3"
        }`}
      >
        {ready ? initial || "简" : <FileText size={13} />}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs text-fg">
          {ready ? profile?.name || "已上传简历" : "未上传简历"}
        </span>
        <span className="block truncate text-3xs text-fg3">
          {ready ? profile?.target || `${profile?.skills?.length ?? 0} 项技能` : "上传 PDF 解锁匹配"}
        </span>
      </span>
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname() ?? "/";
  const [health, setHealth] = useState<Health | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .health()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setHealth(null));
    api
      .profile()
      .then((p) => alive && setProfile(p))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  const online = Boolean(health?.ok);

  return (
    <>
      {/* 桌面端侧边栏 */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[232px] flex-col border-r border-line/70 bg-[#0c111c] lg:flex">
        <div className="flex h-[60px] items-center border-b border-line/60 px-4">
          <Brand />
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          {GROUPS.map((group) => (
            <div key={group.title}>
              <div className="eyebrow px-3 pb-1.5 text-3xs">{group.title}</div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(pathname, item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={`nav-item relative pl-3.5 ${
                        active ? "nav-item-active" : ""
                      }`}
                    >
                      {active && (
                        <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full bg-accent" />
                      )}
                      <Icon
                        size={16}
                        strokeWidth={1.8}
                        className={active ? "text-accent" : "text-fg3"}
                      />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-line/60 p-3">
          <ProfileBadge profile={profile} />
          <div className="mt-2 flex items-center gap-2 rounded-md bg-panel2/40 px-2 py-1.5 text-3xs text-fg3">
            <span
              className={`h-1.5 w-1.5 rounded-full ${online ? "bg-mint" : "bg-rose-400"}`}
            />
            <span>{online ? "API 在线" : "API 未连接"}</span>
            <span className="ml-auto tabular-nums">
              {online ? `${health?.docs ?? 0} 篇 JD` : "8001"}
            </span>
          </div>
        </div>
      </aside>

      {/* 移动端顶栏 */}
      <header className="sticky top-0 z-40 flex h-[56px] items-center justify-between border-b border-line/70 bg-ink/95 px-4 backdrop-blur lg:hidden">
        <Brand />
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <span
            className={`hidden items-center gap-1.5 rounded-full border border-line/70 px-2 py-1 text-3xs text-fg3 sm:inline-flex`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${online ? "bg-mint" : "bg-rose-400"}`}
            />
            {online ? "在线" : "离线"}
          </span>
          <Link
            href="/profile"
            aria-label="我的简历"
            className={`relative flex h-8 w-8 items-center justify-center rounded-full border text-2xs font-medium ${
              profile?.uploaded
                ? "border-mint/30 bg-mint/10 text-mint"
                : "border-line bg-panel2 text-fg3"
            }`}
          >
            {profile?.uploaded ? (
              profile.name?.slice(0, 1) || "简"
            ) : (
              <FileText size={13} />
            )}
            <span
              className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border-2 border-ink ${
                online ? "bg-mint" : "bg-rose-400"
              }`}
            />
          </Link>
        </div>
      </header>

      {/* 移动端底部导航 */}
      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-line/70 bg-[#0b1019]/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
        <div className="grid grid-cols-5">
          {MOBILE.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-col items-center gap-1 py-2 text-3xs transition-colors ${
                  active ? "text-accent" : "text-fg3"
                }`}
              >
                <Icon size={18} strokeWidth={active ? 2.1 : 1.8} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
