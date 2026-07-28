import { describe, expect, it } from "vitest";

import { filterCasesByQuery } from "@/lib/api/client";
import type {
  CaseDetailDto,
  CaseListDto,
  CaseSummaryDto,
  ExplanationDto,
} from "@/lib/api/types";
import { mockCase, mockCaseList } from "@/test/fixtures";

describe("API DTOs (contrato camelCase)", () => {
  it("CaseSummaryDto tiene la forma de CaseSummaryResponse", () => {
    const dto: CaseSummaryDto = mockCase;
    expect(dto).toMatchObject({
      caseId: expect.any(String),
      transactionId: expect.any(String),
      accountId: expect.any(String),
      status: expect.any(String),
      openedAt: expect.any(String),
      score: expect.any(Number),
      isCase: expect.any(Boolean),
      summary: expect.any(String),
    });
    expect("assignedTo" in dto).toBe(true);
  });

  it("CaseListDto tiene items, total, page y pageSize", () => {
    const dto: CaseListDto = mockCaseList;
    expect(dto.items).toHaveLength(2);
    expect(dto.total).toBe(2);
    expect(dto.page).toBe(1);
    expect(dto.pageSize).toBe(20);
  });

  it("ExplanationDto y CaseDetailDto alinean el contrato de detalle", () => {
    const explanation: ExplanationDto = {
      transactionId: "tx-1",
      accountId: "acc-1",
      score: 80,
      threshold: 50,
      isCase: true,
      summary: "Resumen",
      generatedAt: "2026-07-20T12:00:00Z",
      reasons: [
        {
          ruleId: "R1",
          title: "Monto alto",
          description: "Supera umbral",
          detail: "amount=2e6",
          points: 40,
          observed: { amount: 2000000 },
        },
      ],
    };

    const detail: CaseDetailDto = {
      caseId: "case-001",
      transactionId: "tx-1",
      accountId: "acc-1",
      status: "Abierto",
      openedAt: "2026-07-20T12:00:00Z",
      assignedTo: null,
      explanation,
      auditTrail: [{ event: "opened" }],
    };

    expect(detail.explanation.reasons[0]?.ruleId).toBe("R1");
    expect(detail.explanation.isCase).toBe(true);
  });
});

describe("filterCasesByQuery", () => {
  it("filtra por caseId o accountId", () => {
    const byId = filterCasesByQuery(mockCaseList.items, "case-002");
    expect(byId).toHaveLength(1);
    expect(byId[0]?.caseId).toBe("case-002");

    const byAccount = filterCasesByQuery(mockCaseList.items, "acc-100");
    expect(byAccount).toHaveLength(1);
    expect(byAccount[0]?.accountId).toBe("acc-100");
  });

  it("sin query devuelve todos", () => {
    expect(filterCasesByQuery(mockCaseList.items, undefined)).toHaveLength(2);
    expect(filterCasesByQuery(mockCaseList.items, "   ")).toHaveLength(2);
  });
});
