import type { Metadata } from "next";
import "./globals.css";

import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "job-scout · 求职决策系统",
  description:
    "采集真实招聘 JD，用 RAG 做检索问答，给每个岗位算匹配度、生成招呼语和简历改写建议",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-accent focus:px-3 focus:py-2 focus:text-sm focus:text-white"
        >
          跳到主内容
        </a>

        <Sidebar />

        <div className="flex min-h-screen flex-col lg:pl-[232px]">
          <main
            id="main"
            className="mx-auto w-full max-w-[1200px] flex-1 px-4 pb-24 pt-6 sm:px-6 lg:px-8 lg:pb-12 lg:pt-9"
          >
            {children}
          </main>

          <footer className="border-t border-line/60">
            <div className="mx-auto flex w-full max-w-[1200px] flex-wrap items-center justify-between gap-2 px-4 py-5 pb-24 text-2xs text-fg3 sm:px-6 lg:px-8 lg:pb-5">
              <span>job-scout · 本地运行，数据来自公开岗位页面</span>
              <span className="text-fg3/80">FastAPI · Next.js · BM25 + 向量 + RRF</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
