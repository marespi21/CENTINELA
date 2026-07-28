/**
 * Cliente HTTP del navegador.
 * Solo habla con los route handlers de Next (/api/*); nunca conoce la API key.
 */

import type { CaseDetailDto, CaseListDto, CaseListParams } from "./types";
import { ApiError } from "./types";

function buildQuery(params: CaseListParams): string {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.assignedTo) search.set("assignedTo", params.assignedTo);
  if (params.from) search.set("from", params.from);
  if (params.to) search.set("to", params.to);
  if (params.page != null) search.set("page", String(params.page));
  if (params.pageSize != null) search.set("pageSize", String(params.pageSize));
  if (params.q) search.set("q", params.q);
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function bffFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  const response = await fetch(path, { ...init, headers, cache: "no-store" });

  if (!response.ok) {
    let detail = `Error ${response.status}`;
    let code: string | undefined;
    try {
      const body = (await response.json()) as { detail?: string; code?: string };
      if (body.detail) detail = body.detail;
      code = body.code;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, response.status, code);
  }

  return (await response.json()) as T;
}

/** Lista casos vía BFF: GET /api/cases → GET /cases (con API key en servidor). */
export async function listCases(params: CaseListParams = {}): Promise<CaseListDto> {
  return bffFetch<CaseListDto>(`/api/cases${buildQuery(params)}`);
}

/** Detalle de caso vía BFF. */
export async function getCase(caseId: string): Promise<CaseDetailDto> {
  return bffFetch<CaseDetailDto>(`/api/cases/${encodeURIComponent(caseId)}`);
}

/** Filtra filas por id de caso o cuenta (búsqueda de bandeja). */
export function filterCasesByQuery<T extends { caseId: string; accountId: string; transactionId: string }>(
  items: T[],
  q: string | undefined,
): T[] {
  const needle = q?.trim().toLowerCase();
  if (!needle) return items;
  return items.filter(
    (item) =>
      item.caseId.toLowerCase().includes(needle) ||
      item.accountId.toLowerCase().includes(needle) ||
      item.transactionId.toLowerCase().includes(needle),
  );
}
