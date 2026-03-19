import type { ReactNode } from "react";

type Props = {
  eyebrow?: string;
  title: string;
  subtitle: string;
  action?: ReactNode;
};

export default function PageHeader({ eyebrow, title, subtitle, action }: Props) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && (
          <div className="text-xs uppercase tracking-[0.32em] text-[color:var(--muted)]">{eyebrow}</div>
        )}
        <h1 className="font-display text-3xl">{title}</h1>
        <p className="text-sm text-[color:var(--muted)]">{subtitle}</p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
