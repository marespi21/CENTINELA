"use client";

import { cn } from "@/lib/utils/cn";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  className,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  const canPrev = page > 1;
  const canNext = page < totalPages;

  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between",
        className,
      )}
      data-testid="pagination"
    >
      <p className="text-sm text-[var(--muted)]">
        {total === 0 ? (
          "Sin resultados"
        ) : (
          <>
            Mostrando{" "}
            <span className="font-semibold text-[var(--ink)]">
              {from}–{to}
            </span>{" "}
            de <span className="font-semibold text-[var(--ink)]">{total}</span>
          </>
        )}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={!canPrev}
          onClick={() => onPageChange(page - 1)}
          className="btn-ghost"
          aria-label="Página anterior"
        >
          Anterior
        </button>
        <span className="min-w-[5rem] text-center font-mono text-xs text-[var(--muted)]">
          {page} / {totalPages}
        </span>
        <button
          type="button"
          disabled={!canNext}
          onClick={() => onPageChange(page + 1)}
          className="btn-ghost"
          aria-label="Página siguiente"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
