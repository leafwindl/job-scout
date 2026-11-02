import type { ReactNode } from "react";

type Props = {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
};

export default function PageHeader({ eyebrow, title, description, actions, meta }: Props) {
  return (
    <header className="animate-rise">
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <div className="min-w-0">
          {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
          <h1 className="page-title">{title}</h1>
          {description && (
            <p className="mt-2 max-w-2xl text-[13px] leading-[1.7] text-fg3">{description}</p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {meta && <div className="mt-4">{meta}</div>}
    </header>
  );
}
