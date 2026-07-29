/**
 * Cliente HTTP del lado servidor (BFF).
 * Usa NEXT_PUBLIC_API_BASE + ANALYST_API_KEY (nunca expuesta al navegador).
 */

import type { CaseDetailDto, CaseDocumentListDto, CaseListDto, CaseListParams, AssignCaseDto, ResolveCaseDto } from "./types";
import { ApiError } from "./types";
import { mockCaseList, mockDocumentsFallback } from "@/test/fixtures";

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

const mockDetailFallback: CaseDetailDto = {
  caseId: "case-001",
  transactionId: "TX-998811",
  accountId: "ACC-55102",
  status: "Abierto",
  openedAt: "2026-07-28T10:15:00Z",
  assignedTo: null,
  explanation: {
    transactionId: "TX-998811",
    accountId: "ACC-55102",
    score: 85,
    threshold: 70,
    isCase: true,
    summary: "Riesgo Alto: Múltiples transacciones en comercios inusuales.",
    generatedAt: "2026-07-28T10:15:00Z",
    reasons: [
      {
        ruleId: "GEO_IMPOSSIBLE",
        title: "Ubicación Geográfica Imposible",
        description: "Dos transacciones registradas en ciudades distintas.",
        detail: "Distancia: 11,000 km en 15 minutos.",
        points: 50,
        observed: { lastCity: "Bogotá", currentCity: "Tokyo", amount: 12500000 },
      },
    ],
  },
  auditTrail: [
    {
      id: 1,
      entidad: "casos",
      caso_id: "case-001",
      accion: "CREACION_CASO",
      usuario_accion: "SISTEMA_SCORING",
      fecha_registro: "2026-07-28T10:15:00Z",
    },
  ],
};

/** GET /cases — listado paginado con filtros. */
export async function fetchCases(params: CaseListParams = {}): Promise<CaseListDto> {
  const apiParams: CaseListParams = {
    status: params.status,
    assignedTo: params.assignedTo,
    from: params.from,
    to: params.to,
    page: params.page,
    pageSize: params.pageSize,
  };
  try {
    return await serverFetch<CaseListDto>(`/cases${buildQuery(apiParams)}`);
  } catch (err: unknown) {
    if (err instanceof ApiError && err.status === 502) {
      console.warn("[BFF Server] Backend FastAPI offline. Usando datos mock de desarrollo.");
      return mockCaseList;
    }
    throw err;
  }
}

/** GET /cases/{caseId} — detalle. */
export async function fetchCaseDetail(caseId: string): Promise<CaseDetailDto> {
  try {
    return await serverFetch<CaseDetailDto>(`/cases/${encodeURIComponent(caseId)}`);
  } catch (err: unknown) {
    if (err instanceof ApiError && err.status === 502) {
      console.warn(`[BFF Server] Backend FastAPI offline para caso ${caseId}. Usando datos mock.`);
      return { ...mockDetailFallback, caseId };
    }
    throw err;
  }
}

/** GET /cases/{caseId}/documents — documentos con URLs SAS temporales. */
export async function fetchCaseDocuments(caseId: string): Promise<CaseDocumentListDto> {
  try {
    return await serverFetch<CaseDocumentListDto>(
      `/cases/${encodeURIComponent(caseId)}/documents`,
    );
  } catch (err: unknown) {
    if (err instanceof ApiError && err.status === 502) {
      console.warn(`[BFF Server] Backend FastAPI offline para documentos de ${caseId}. Usando datos mock.`);
      return mockDocumentsFallback;
    }
    throw err;
  }
}

/** POST /cases/{caseId}/assign — asignación de caso. */
export async function assignCase(caseId: string, body: AssignCaseDto = {}): Promise<CaseDetailDto> {
  try {
    return await serverFetch<CaseDetailDto>(`/cases/${encodeURIComponent(caseId)}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err: unknown) {
    if (err instanceof ApiError && err.status === 502) {
      const assignee = body.assigneeId || "analista.juanjo";
      return {
        ...mockDetailFallback,
        caseId,
        status: "En Investigacion",
        assignedTo: assignee,
        auditTrail: [
          ...mockDetailFallback.auditTrail,
          {
            id: Date.now(),
            entidad: "asignaciones",
            caso_id: caseId,
            accion: "ASIGNAR_CASO",
            usuario_accion: assignee,
            fecha_registro: new Date().toISOString(),
          },
        ],
      };
    }
    throw err;
  }
}

/** POST /cases/{caseId}/resolve — resolución de caso. */
export async function resolveCase(caseId: string, body: ResolveCaseDto): Promise<CaseDetailDto> {
  try {
    return await serverFetch<CaseDetailDto>(`/cases/${encodeURIComponent(caseId)}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err: unknown) {
    if (err instanceof ApiError && err.status === 502) {
      return {
        ...mockDetailFallback,
        caseId,
        status: "Resuelto",
        auditTrail: [
          ...mockDetailFallback.auditTrail,
          {
            id: Date.now(),
            entidad: "resoluciones",
            caso_id: caseId,
            accion: "RESOLVER_CASO",
            usuario_accion: "ANALISTA",
            fecha_registro: new Date().toISOString(),
            estado_nuevo: { status: "Resuelto", resolution: body.resolution, note: body.note },
          },
        ],
      };
    }
    throw err;
  }
}

export { apiBaseUrl };
