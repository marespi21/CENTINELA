import { cn } from "@/lib/utils/cn";

interface LoadingStateProps {
  label?: string;
  className?: string;
}

export function LoadingState({
  label = "Cargando…",
  className,
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 py-16 text-[var(--muted)]",
        className,
      )}
      role="status"
      aria-live="polite"
      data-testid="loading-state"
    >
      <span className="h-9 w-9 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]" />
      <p className="text-sm tracking-wide">{label}</p>
    </div>
  );
}
