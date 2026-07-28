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

  function onPageChange(page: number) {
    const next = new URLSearchParams(searchParams.toString());
    next.set("page", String(page));
    router.push(`/cases?${next.toString()}`);
  }

  return (
    <div className="space-y-6">
      <header className="animate-fade-up space-y-2">
        <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--muted)]">
          Bandeja
        </p>
        <h1 className="font-display text-3xl tracking-tight text-[var(--ink)] sm:text-4xl">
          Casos de fraude
        </h1>
        <p className="max-w-2xl text-sm leading-relaxed text-[var(--muted)] sm:text-base">
          Revisa, filtra y abre casos abiertos por el motor de scoring. La API key
          del analista permanece en el servidor Next (BFF).
        </p>
      </header>

      <CasesFilters initial={params} />

      <section className="panel animate-fade-up-delay overflow-hidden">
        {query.isLoading ? (
          <LoadingState label="Consultando bandeja de casos…" />
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
            description="Ajusta el estado, el rango de fechas o la búsqueda por ID/cuenta."
          />
        ) : null}

        {query.isSuccess && query.data.items.length > 0 ? (
          <>
            <CasesTable items={query.data.items} />
            <div className="border-t border-[var(--border)] px-4 py-3 sm:px-5">
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
