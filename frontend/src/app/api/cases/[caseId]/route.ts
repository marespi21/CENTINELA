import { NextResponse } from "next/server";

import { fetchCaseDetail } from "@/lib/api/server";
import { ApiError } from "@/lib/api/types";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ caseId: string }> };

/**
 * BFF: proxy de GET /cases/{caseId}.
 * Base para las historias de detalle (HU posteriores).
 */
export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<NextResponse> {
  try {
    const { caseId } = await context.params;
    const data = await fetchCaseDetail(caseId);
    return NextResponse.json(data);
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
