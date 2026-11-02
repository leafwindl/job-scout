"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const MAIN = [
  { href: "/", label: "概览" },
  { href: "/jobs", label: "岗位" },
  { href: "/prep", label: "准备" },
  { href: "/ask", label: "问答" },
];

const TOOLS = [
  { href: "/profile", label: "我的" },
  { href: "/collect", label: "采集" },
  { href: "/dashboard", label: "看板" },
  { href: "/eval", label: "评测" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function Nav() {
  const pathname = usePathname() ?? "/";

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-ink/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3.5">
        <Link href="/" className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/15 text-xs font-semibold text-accent">
            JS
          </span>
          <span className="text-base font-semibold text-slate-100">job-scout</span>
        </Link>

        <nav className="flex items-center gap-1">
          {MAIN.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-panel2 text-slate-100"
                    : "text-slate-400 hover:bg-panel2/60 hover:text-slate-200"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1 border-l border-line pl-4">
          {TOOLS.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-2.5 py-1.5 text-xs transition-colors ${
                  active
                    ? "bg-panel2 text-slate-200"
                    : "text-slate-500 hover:bg-panel2/60 hover:text-slate-300"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </header>
  );
}
