"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo } from "react";

import { CasesFilters } from "@/components/cases/CasesFilters";
import { CasesTable } from "@/components/cases/CasesTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Pagination } from "@/components/ui/Pagination";
import { listCases } from "@/lib/api/client";
import type { CaseListParams } from "@/lib/api/types";
import { queryKeys } from "@/lib/query/keys";

const DEFAULT_PAGE_SIZE = 20;

function statusSummary(items: { status: string }[]) {
  return items.reduce(
    (summary, item) => {
      const status = item.status.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
      if (status === "abierto") summary.open += 1;
      if (status === "asignado" || status === "en investigacion") summary.inProgress += 1;
      if (status === "resuelto") summary.resolved += 1;
      return summary;
    },
    { open: 0, inProgress: 0, resolved: 0 },
  );
}

export function CasesInbox() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const params = useMemo<CaseListParams>(() => {
    const page = Number(searchParams.get("page") || "1");
    return {
      status: searchParams.get("status") ?? undefined,
      from: searchParams.get("from") ?? undefined,
      to: searchParams.get("to") ?? undefined,
      q: searchParams.get("q") ?? undefined,
      page: Number.isFinite(page) && page > 0 ? page : 1,
      pageSize: DEFAULT_PAGE_SIZE,
    };
  }, [searchParams]);

  const query = useQuery({
    queryKey: queryKeys.cases.list(params),
    queryFn: () => listCases(params),
  });
  // Resumen de la página visible, no del total del sistema.
  const summary = statusSummary(query.data?.items ?? []);

  function onPageChange(page: number) {
    const next = new URLSearchParams(searchParams.toString());
    next.set("page", String(page));
    router.push(`/cases?${next.toString()}`);
  }

  return (
    <div className="space-y-6">
      <header className="animate-fade-up flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-[var(--accent)]">Bandeja operativa</p>
          <h1 className="font-display text-4xl font-semibold text-[var(--ink)] sm:text-5xl">
            Casos de fraude
          </h1>
          <p className="max-w-xl text-[15px] leading-relaxed text-[var(--muted)]">
            Filtra, prioriza y abre expedientes detectados por el motor de scoring.
          </p>
        </div>

        <div className="flex gap-3">
          <div className="min-w-[7.5rem] rounded-2xl border border-[var(--border)] bg-white px-4 py-3 shadow-sm">
            <p className="text-xs font-medium text-[var(--muted)]">Total</p>
            <p className="mt-1 font-display text-2xl font-semibold tabular-nums text-[var(--ink)]">
              {query.isLoading ? "—" : (query.data?.total ?? 0)}
            </p>
          </div>
          <div className="min-w-[7.5rem] rounded-2xl border border-[var(--border)] bg-white px-4 py-3 shadow-sm">
            <p className="text-xs font-medium text-[var(--muted)]">Vista</p>
            <p className="mt-1 font-display text-2xl font-semibold text-[var(--ink)]">
              {params.status || "Todas"}
            </p>
          </div>
        </div>
      </header>

      <section aria-label="Resumen por estado" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          ["Abiertos", summary.open],
          ["En investigación", summary.inProgress],
          ["Resueltos", summary.resolved],
        ].map(([label, count]) => (
          <div
            key={String(label)}
            className="rounded-2xl border border-[var(--border)] bg-white px-4 py-3 shadow-sm"
          >
            <p className="text-xs font-medium text-[var(--muted)]">{label}</p>
            <p className="mt-1 font-display text-2xl font-semibold tabular-nums text-[var(--ink)]">
              {query.isLoading ? "—" : count}
            </p>
          </div>
        ))}
      </section>

      <CasesFilters initial={params} />

      <section className="panel animate-fade-up-delay overflow-hidden">
        {query.isLoading ? (
          <LoadingState label="Cargando casos…" />
        ) : null}

        {query.isError ? (
          <ErrorState
            message={
              query.error instanceof Error
                ? query.error.message
                : "Error desconocido al cargar los casos."
            }
            onRetry={() => void query.refetch()}
          />
        ) : null}

        {query.isSuccess && query.data.items.length === 0 ? (
          <EmptyState
            title="No hay casos con estos filtros"
            description="Prueba otro estado, rango de fechas o búsqueda por ID/cuenta."
          />
        ) : null}

        {query.isSuccess && query.data.items.length > 0 ? (
          <>
            <CasesTable items={query.data.items} />
            <div className="border-t border-[var(--border)] px-4 py-3.5 sm:px-5">
              <Pagination
                page={query.data.page}
                pageSize={query.data.pageSize}
                total={query.data.total}
                onPageChange={onPageChange}
              />
            </div>
          </>
        ) : null}
      </section>
    </div>
  );
}
