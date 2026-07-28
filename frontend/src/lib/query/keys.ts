import type { CaseListParams } from "@/lib/api/types";

export const queryKeys = {
  cases: {
    all: ["cases"] as const,
    list: (params: CaseListParams) => ["cases", "list", params] as const,
    detail: (caseId: string) => ["cases", "detail", caseId] as const,
  },
};
