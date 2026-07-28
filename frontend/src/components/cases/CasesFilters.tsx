"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useState, useTransition } from "react";

import type { CaseListParams } from "@/lib/api/types";

const STATUS_OPTIONS = [
  { value: "", label: "Todos los estados" },
  { value: "Abierto", label: "Abierto" },
  { value: "Asignado", label: "Asignado" },
  { value: "Resuelto", label: "Resuelto" },
] as const;

interface CasesFiltersProps {
  initial: CaseListParams;
}

export function CasesFilters({ initial }: CasesFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const [q, setQ] = useState(initial.q ?? "");
  const [status, setStatus] = useState(initial.status ?? "");
  const [from, setFrom] = useState(toDateInput(initial.from));
  const [to, setTo] = useState(toDateInput(initial.to));

  const apply = useCallback(
    (overrides: Partial<CaseListParams> = {}) => {
      const next = new URLSearchParams(searchParams.toString());
      const values: CaseListParams = {
        q: overrides.q !== undefined ? overrides.q : q,
        status: overrides.status !== undefined ? overrides.status : status,
        from: overrides.from !== undefined ? overrides.from : fromDateInput(from),
        to: overrides.to !== undefined ? overrides.to : fromDateInput(to, true),
        page: 1,
      };

      setParam(next, "q", values.q);
      setParam(next, "status", values.status);
      setParam(next, "from", values.from);
      setParam(next, "to", values.to);
      next.set("page", "1");

      startTransition(() => {
        router.push(`/cases?${next.toString()}`);
      });
    },
    [from, q, router, searchParams, status, to],
  );

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    apply();
  }

  function onReset() {
    setQ("");
    setStatus("");
    setFrom("");
    setTo("");
    startTransition(() => {
      router.push("/cases");
    });
  }

  return (
    <form
      onSubmit={onSubmit}
      className="panel animate-fade-up space-y-4 p-4 sm:p-5"
      data-testid="cases-filters"
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label className="field">
          <span className="field-label">Buscar</span>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="ID de caso o cuenta"
            className="field-input font-mono text-[13px]"
            data-testid="filter-search"
          />
        </label>

        <label className="field">
          <span className="field-label">Estado</span>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              apply({ status: e.target.value });
            }}
            className="field-input"
            data-testid="filter-status"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value || "all"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-label">Desde</span>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="field-input"
            data-testid="filter-from"
          />
        </label>

        <label className="field">
          <span className="field-label">Hasta</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="field-input"
            data-testid="filter-to"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button type="submit" className="btn-primary" disabled={isPending}>
          Aplicar filtros
        </button>
        <button type="button" className="btn-ghost" onClick={onReset} disabled={isPending}>
          Limpiar
        </button>
        {isPending ? (
          <span className="text-xs text-[var(--muted)]">Actualizando…</span>
        ) : null}
      </div>
    </form>
  );
}

function setParam(params: URLSearchParams, key: string, value?: string) {
  if (value?.trim()) params.set(key, value.trim());
  else params.delete(key);
}

function toDateInput(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toISOString().slice(0, 10);
}

function fromDateInput(value: string, endOfDay = false): string | undefined {
  if (!value) return undefined;
  if (endOfDay) return `${value}T23:59:59.999Z`;
  return `${value}T00:00:00.000Z`;
}
