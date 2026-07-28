import { NextRequest, NextResponse } from "next/server";

import { filterCasesByQuery } from "@/lib/api/client";
import { fetchCases } from "@/lib/api/server";
import { ApiError, type CaseListParams } from "@/lib/api/types";

export const dynamic = "force-dynamic";

function parseParams(request: NextRequest): CaseListParams {
  const sp = request.nextUrl.searchParams;
  const page = sp.get("page");
  const pageSize = sp.get("pageSize");
  return {
    status: sp.get("status") ?? undefined,
    assignedTo: sp.get("assignedTo") ?? undefined,
    from: sp.get("from") ?? undefined,
    to: sp.get("to") ?? undefined,
    page: page ? Number(page) : undefined,
    pageSize: pageSize ? Number(pageSize) : undefined,
    q: sp.get("q") ?? undefined,
  };
}

/**
 * BFF: proxy de GET /cases.
 * Inyecta X-API-Key en el servidor; el navegador solo llama /api/cases.
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const params = parseParams(request);
    const data = await fetchCases(params);
    const items = filterCasesByQuery(data.items, params.q);
    return NextResponse.json({
      ...data,
      items,
      // Si hay búsqueda local, el total reflejado es el filtrado de la página.
      total: params.q?.trim() ? items.length : data.total,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message, code: error.code },
        { status: error.status },
      );
    }
    return NextResponse.json(
      { detail: "Error interno del BFF", code: "BFF_ERROR" },
      { status: 500 },
    );
  }
}
