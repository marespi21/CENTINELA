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
        "flex flex-col items-center justify-center gap-2 px-6 py-20 text-center",
        className,
      )}
      data-testid="empty-state"
    >
      <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)]">
        <span className="font-display text-lg font-semibold">0</span>
      </div>
      <h3 className="font-display text-xl font-semibold text-[var(--ink)]">{title}</h3>
      {description ? (
        <p className="max-w-md text-sm text-[var(--muted)]">{description}</p>
      ) : null}
    </div>
  );
}
