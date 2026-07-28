import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CasesFilters } from "@/components/cases/CasesFilters";

const push = vi.fn();
let currentParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  useSearchParams: () => currentParams,
}));

afterEach(() => {
  cleanup();
});

describe("CasesFilters", () => {
  beforeEach(() => {
    push.mockClear();
    currentParams = new URLSearchParams();
  });

  it("aplica búsqueda y estado en la URL", async () => {
    const user = userEvent.setup();
    render(
      createElement(CasesFilters, {
        initial: { page: 1, pageSize: 20 },
      }),
    );

    await user.type(screen.getByTestId("filter-search"), "acc-100");
    await user.selectOptions(screen.getByTestId("filter-status"), "Abierto");
    await user.click(screen.getByRole("button", { name: /aplicar filtros/i }));

    expect(push).toHaveBeenCalled();
    const url = String(push.mock.calls.at(-1)?.[0]);
    expect(url).toContain("/cases?");
    expect(url).toContain("q=acc-100");
    expect(url).toContain("status=Abierto");
    expect(url).toContain("page=1");
  });
});
