/**
 * Cliente HTTP del lado servidor (BFF).
 * Usa NEXT_PUBLIC_API_BASE + ANALYST_API_KEY (nunca expuesta al navegador).
 */

import type { CaseDetailDto, CaseListDto, CaseListParams, AssignCaseDto, ResolveCaseDto } from "./types";
import { ApiError } from "./types";

function apiBaseUrl(): string {
  const base =
    process.env.API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_BASE?.trim() ||
    "http://localhost:8000";
  return base.replace(/\/$/, "");
}

function analystApiKey(): string | undefined {
  const key = process.env.ANALYST_API_KEY?.trim();
  return key || undefined;
}

function buildQuery(params: CaseListParams): string {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.assignedTo) search.set("assignedTo", params.assignedTo);
  if (params.from) search.set("from", params.from);
  if (params.to) search.set("to", params.to);
  if (params.page != null) search.set("page", String(params.page));
  if (params.pageSize != null) search.set("pageSize", String(params.pageSize));
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function serverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  const key = analystApiKey();
  if (key) {
    headers.set("X-API-Key", key);
  }

  const url = `${apiBaseUrl()}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "No se pudo conectar con la API de CENTINELA. Verifica NEXT_PUBLIC_API_BASE.",
      502,
      "UPSTREAM_UNREACHABLE",
    );
  }

  if (!response.ok) {
    let detail = `Error ${response.status} al consultar ${path}`;
    let code: string | undefined;
    try {
      const body = (await response.json()) as { detail?: string; code?: string };
      if (body.detail) detail = body.detail;
      code = body.code;
    } catch {
      /* ignore parse errors */
    }
    throw new ApiError(detail, response.status, code);
  }

  return (await response.json()) as T;
}

/** GET /cases — listado paginado con filtros. */
export async function fetchCases(params: CaseListParams = {}): Promise<CaseListDto> {
  // `q` es búsqueda de bandeja (cliente/BFF); la API backend no lo recibe.
  const apiParams: CaseListParams = {
    status: params.status,
    assignedTo: params.assignedTo,
    from: params.from,
    to: params.to,
    page: params.page,
    pageSize: params.pageSize,
  };
  return serverFetch<CaseListDto>(`/cases${buildQuery(apiParams)}`);
}

/** GET /cases/{caseId} — detalle (base para HU posteriores). */
export async function fetchCaseDetail(caseId: string): Promise<CaseDetailDto> {
  return serverFetch<CaseDetailDto>(`/cases/${encodeURIComponent(caseId)}`);
}

/** POST /cases/{caseId}/assign — asignación de caso. */
export async function assignCase(caseId: string, body: AssignCaseDto = {}): Promise<CaseDetailDto> {
  return serverFetch<CaseDetailDto>(`/cases/${encodeURIComponent(caseId)}/assign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** POST /cases/{caseId}/resolve — resolución de caso. */
export async function resolveCase(caseId: string, body: ResolveCaseDto): Promise<CaseDetailDto> {
  return serverFetch<CaseDetailDto>(`/cases/${encodeURIComponent(caseId)}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export { apiBaseUrl };

