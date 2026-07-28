import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CasesTable } from "@/components/cases/CasesTable";
import { Pagination } from "@/components/ui/Pagination";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { mockCaseList } from "@/test/fixtures";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams("page=1"),
  usePathname: () => "/cases",
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => createElement("a", { href, ...rest }, children),
}));

function renderWithQuery(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(createElement(QueryClientProvider, { client }, ui));
}

afterEach(() => {
  cleanup();
});

describe("CasesTable", () => {
  beforeEach(() => {
    push.mockClear();
  });

  it("renderiza filas con estado, score y enlace al detalle", () => {
    renderWithQuery(createElement(CasesTable, { items: mockCaseList.items }));

    const table = screen.getByTestId("cases-table");
    expect(within(table).getByText("acc-100")).toBeInTheDocument();
    expect(within(table).getByText("Abierto")).toBeInTheDocument();
    expect(within(table).getByText("72")).toBeInTheDocument();

    const link = within(table).getByRole("link", { name: /case-001/i });
    expect(link).toHaveAttribute("href", "/cases/case-001");
  });

  it("navega al detalle al hacer click en la fila", async () => {
    const user = userEvent.setup();
    renderWithQuery(createElement(CasesTable, { items: mockCaseList.items }));

    const table = screen.getByTestId("cases-table");
    await user.click(within(table).getByText("acc-100"));
    expect(push).toHaveBeenCalledWith("/cases/case-001");
  });
});

describe("Pagination", () => {
  it("muestra rango y navega de página", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();

    render(
      createElement(Pagination, {
        page: 1,
        pageSize: 20,
        total: 45,
        onPageChange,
      }),
    );

    const pagination = screen.getByTestId("pagination");
    expect(pagination).toHaveTextContent("1–20");
    expect(pagination).toHaveTextContent("45");

    await user.click(within(pagination).getByRole("button", { name: /siguiente/i }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("deshabilita anterior en la primera página", () => {
    render(
      createElement(Pagination, {
        page: 1,
        pageSize: 20,
        total: 45,
        onPageChange: vi.fn(),
      }),
    );
    const pagination = screen.getByTestId("pagination");
    expect(
      within(pagination).getByRole("button", { name: /anterior/i }),
    ).toBeDisabled();
  });
});

describe("StatusBadge", () => {
  it("muestra el estado del caso", () => {
    render(createElement(StatusBadge, { status: "Resuelto" }));
    expect(screen.getByText("Resuelto")).toBeInTheDocument();
  });
});
