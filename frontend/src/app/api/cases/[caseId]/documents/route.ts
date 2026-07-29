import { NextResponse } from "next/server";

import { fetchCaseDocuments } from "@/lib/api/server";
import { ApiError } from "@/lib/api/types";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ caseId: string }> };

/** BFF: proxy de GET /cases/{caseId}/documents. */
export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<NextResponse> {
  try {
    const { caseId } = await context.params;
    const data = await fetchCaseDocuments(caseId);
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
