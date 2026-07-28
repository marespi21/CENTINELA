import type { CaseListDto, CaseSummaryDto } from "@/lib/api/types";

export const mockCase: CaseSummaryDto = {
  caseId: "case-001",
  transactionId: "tx-aaa-bbb",
  accountId: "acc-100",
  status: "Abierto",
  openedAt: "2026-07-20T12:00:00Z",
  score: 72,
  isCase: true,
  summary: "Monto alto en categoría de riesgo",
  assignedTo: null,
};

export const mockCaseList: CaseListDto = {
  items: [
    mockCase,
    {
      ...mockCase,
      caseId: "case-002",
      accountId: "acc-200",
      status: "Resuelto",
      score: 55,
      assignedTo: "ana-1",
      summary: "Caso resuelto tras revisión",
      openedAt: "2026-07-19T09:30:00Z",
    },
  ],
  total: 2,
  page: 1,
  pageSize: 20,
};
