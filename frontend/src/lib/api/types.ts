/**
 * DTOs tipados del contrato HTTP de la API CENTINELA (camelCase).
 * Fuente de verdad: backend/app/presentation/schemas/case_schema.py
 * No duplicar formas aparte de estos tipos.
 */

export type CaseStatus =
  | "Abierto"
  | "En Investigacion"
  | "Resuelto"
  | "Cerrado"
  | string;

/** Motivo de la explicación (ExplanationReasonSchema). */
export interface ExplanationReasonDto {
  ruleId: string;
  title: string;
  description: string;
  detail: string;
  points: number;
  observed: Record<string, unknown>;
}

/** Explicación legible del scoring (ExplanationSchema / ExplanationDto). */
export interface ExplanationDto {
  transactionId: string;
  accountId: string;
  score: number;
  threshold: number;
  isCase: boolean;
  summary: string;
  generatedAt: string;
  reasons: ExplanationReasonDto[];
}

/** Fila de la bandeja (CaseSummaryResponse / CaseSummaryDto). */
export interface CaseSummaryDto {
  caseId: string;
  transactionId: string;
  accountId: string;
  status: CaseStatus;
  openedAt: string;
  score: number;
  isCase: boolean;
  summary: string;
  assignedTo: string | null;
}

/** Detalle de caso (CaseDetailResponse / CaseDetailDto). */
export interface CaseDetailDto {
  caseId: string;
  transactionId: string;
  accountId: string;
  status: CaseStatus;
  openedAt: string;
  assignedTo: string | null;
  explanation: ExplanationDto;
  auditTrail: Record<string, unknown>[];
}

/** Respuesta paginada de GET /cases (CaseListResponse). */
export interface CaseListDto {
  items: CaseSummaryDto[];
  total: number;
  page: number;
  pageSize: number;
}

/** Query params de GET /cases. */
export interface CaseListParams {
  status?: string;
  assignedTo?: string;
  from?: string;
  to?: string;
  page?: number;
  pageSize?: number;
  /** Búsqueda local por id/cuenta (filtrado en cliente sobre la página). */
  q?: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export interface AssignCaseDto {
  assigneeId?: string;
}

export interface ResolveCaseDto {
  resolution: string;
  note?: string;
}

