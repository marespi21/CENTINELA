import { cn } from "@/lib/utils/cn";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "No se pudo cargar",
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-16 text-center",
        className,
      )}
      role="alert"
      data-testid="error-state"
    >
      <div className="mb-1 flex h-12 w-12 items-center justify-center rounded-full bg-rose-50 ring-1 ring-rose-200">
        <span className="font-mono text-sm text-rose-700">!</span>
      </div>
      <h3 className="font-display text-lg text-[var(--ink)]">{title}</h3>
      <p className="max-w-md text-sm text-[var(--muted)]">{message}</p>
      {onRetry ? (
        <button type="button" onClick={onRetry} className="btn-primary mt-2">
          Reintentar
        </button>
      ) : null}
    </div>
  );
}
