import { cn } from "@/lib/utils/cn";

interface EmptyStateProps {
  title: string;
  description?: string;
  className?: string;
}

export function EmptyState({ title, description, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 px-6 py-16 text-center",
        className,
      )}
      data-testid="empty-state"
    >
      <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--surface-muted)] ring-1 ring-[var(--border)]">
        <span className="font-mono text-xs text-[var(--muted)]">0</span>
      </div>
      <h3 className="font-display text-lg text-[var(--ink)]">{title}</h3>
      {description ? (
        <p className="max-w-md text-sm text-[var(--muted)]">{description}</p>
      ) : null}
    </div>
  );
}
