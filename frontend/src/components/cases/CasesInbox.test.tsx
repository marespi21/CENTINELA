import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listCases } from "@/lib/api/client";
import { mockCaseList } from "@/test/fixtures";

import { CasesInbox } from "./CasesInbox";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("page=1"),
}));

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listCases: vi.fn() };
});

function renderInbox() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <CasesInbox />
    </QueryClientProvider>,
  );
}

describe("CasesInbox", () => {
  beforeEach(() => vi.resetAllMocks());

  it("calcula el resumen con los casos de la página visible", async () => {
    vi.mocked(listCases).mockResolvedValue({
      ...mockCaseList,
      items: [
        mockCaseList.items[0],
        { ...mockCaseList.items[0], caseId: "case-002", status: "En Investigacion" },
        { ...mockCaseList.items[0], caseId: "case-003", status: "Resuelto" },
        { ...mockCaseList.items[0], caseId: "case-004", status: "Abierto" },
      ],
      total: 99,
    });
    renderInbox();

    const summary = await screen.findByLabelText("Resumen por estado");
    await waitFor(() => expect(summary).toHaveTextContent("2"));
    expect(summary).toHaveTextContent("Abiertos");
    expect(summary).toHaveTextContent("En investigación");
    expect(summary).toHaveTextContent("Resueltos");
    expect(summary).toHaveTextContent("2");
    expect(summary).toHaveTextContent("1");
  });
});
