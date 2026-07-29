import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listCaseDocuments } from "@/lib/api/client";
import type { CaseDocumentListDto } from "@/lib/api/types";

import { DocumentsCard } from "./DocumentsCard";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return { ...actual, listCaseDocuments: vi.fn() };
});

const documents: CaseDocumentListDto = {
  items: [
    {
      blobName: "cases/case-001/reporte.pdf",
      filename: "reporte.pdf",
      contentType: "application/pdf",
      url: "https://example.test/reporte.pdf?temporary-token",
      expiresAt: "2026-07-29T10:15:00Z",
    },
  ],
};

function renderCard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DocumentsCard caseId="case-001" />
    </QueryClientProvider>,
  );
}

describe("DocumentsCard", () => {
  beforeEach(() => vi.resetAllMocks());

  it("muestra el nombre y enlace de cada documento", async () => {
    vi.mocked(listCaseDocuments).mockResolvedValue(documents);
    renderCard();

    expect(await screen.findByText("reporte.pdf")).toBeInTheDocument();
    expect(screen.getByText("application/pdf")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /abrir documento reporte.pdf/i })).toHaveAttribute(
      "href",
      documents.items[0].url,
    );
  });

  it("muestra EmptyState cuando no hay documentos", async () => {
    vi.mocked(listCaseDocuments).mockResolvedValue({ items: [] });
    renderCard();

    expect(await screen.findByText("Este caso no tiene documentos adjuntos")).toBeInTheDocument();
  });

  it("muestra ErrorState y permite reintentar", async () => {
    vi.mocked(listCaseDocuments)
      .mockRejectedValueOnce(new Error("Servicio no disponible"))
      .mockResolvedValueOnce(documents);
    renderCard();

    expect(await screen.findByTestId("error-state")).toHaveTextContent("Servicio no disponible");
    fireEvent.click(screen.getByRole("button", { name: /reintentar/i }));

    await waitFor(() => expect(listCaseDocuments).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("reporte.pdf")).toBeInTheDocument();
  });
});
