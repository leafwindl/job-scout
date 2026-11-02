import type { Metadata } from "next";
import "./globals.css";

import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "job-scout · 求职决策系统",
  description: "采集真实招聘 JD，用 RAG 做检索问答，给每个岗位算匹配度、生成招呼语和简历改写建议",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Nav />
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mt-16 border-t border-line">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-6 py-6 text-xs text-slate-600">
            <span>job-scout · 个人项目，数据来自公开岗位页面，仅本地使用</span>
            <span>FastAPI + Next.js + BM25/向量 + RRF</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
