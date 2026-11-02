import Link from "next/link";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[55vh] items-center justify-center">
      <div className="card w-full max-w-md px-6 py-10 text-center">
        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-panel2 text-fg3">
          <Compass size={20} strokeWidth={1.6} />
        </span>
        <h1 className="mt-3 text-[16px] font-medium text-fg">这个页面游走了</h1>
        <p className="mt-1.5 text-[13px] leading-[1.7] text-fg3">
          岗位可能已下架，或者链接拼错了。回到岗位库再找找。
        </p>
        <div className="mt-5 flex justify-center gap-2">
          <Link href="/" className="btn btn-primary btn-sm">
            回概览
          </Link>
          <Link href="/jobs" className="btn btn-ghost btn-sm">
            去岗位库
          </Link>
        </div>
      </div>
    </div>
  );
}
