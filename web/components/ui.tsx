import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

const TONE_TEXT: Record<string, string> = {
  default: "text-fg",
  accent: "text-accent",
  mint: "text-mint",
  amber: "text-amber-400",
  rose: "text-rose-400",
};

export function Stat({
  label,
  value,
  unit,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: ReactNode;
  tone?: keyof typeof TONE_TEXT;
}) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-1">
        <span
          className={`text-[22px] font-semibold leading-none tracking-tight tabular-nums ${TONE_TEXT[tone]}`}
        >
          {value}
        </span>
        {unit && <span className="text-2xs text-fg3">{unit}</span>}
      </div>
      {hint && <div className="mt-1 text-3xs leading-4 text-fg3">{hint}</div>}
    </div>
  );
}

export function SectionHeader({
  title,
  hint,
  action,
  icon: Icon,
}: {
  title: string;
  hint?: ReactNode;
  action?: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex min-w-0 items-center gap-2">
        {Icon && <Icon size={15} strokeWidth={1.9} className="shrink-0 text-fg3" />}
        <h2 className="section-title">{title}</h2>
        {hint && (
          <span className="truncate text-2xs font-normal text-fg3">{hint}</span>
        )}
      </div>
      {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  children,
  compact = false,
}: {
  icon: LucideIcon;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center px-6 text-center ${
        compact ? "py-8" : "py-12"
      }`}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-panel2 text-fg3">
        <Icon size={18} strokeWidth={1.7} />
      </div>
      <div className="mt-3 text-[13px] font-medium text-fg">{title}</div>
      {description && (
        <p className="mt-1 max-w-sm text-xs leading-[1.7] text-fg3">{description}</p>
      )}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

const TONE_BG: Record<string, string> = {
  default: "bg-fg3",
  accent: "bg-accent",
  mint: "bg-mint",
  amber: "bg-amber-400",
  rose: "bg-rose-400",
};

export function ProgressBar({
  value,
  tone = "accent",
  height = "h-1.5",
}: {
  value: number;
  tone?: keyof typeof TONE_BG;
  height?: string;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className={`w-full overflow-hidden rounded-full bg-panel3/70 ${height}`}>
      <div
        className={`h-full rounded-full transition-[width] duration-500 ${TONE_BG[tone]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function SkeletonBlock({ className = "h-4 w-full" }: { className?: string }) {
  return <div className={`skel ${className}`} />;
}
