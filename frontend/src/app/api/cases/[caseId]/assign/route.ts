import { NextResponse } from "next/server";
import { assignCase } from "@/lib/api/server";
import { ApiError } from "@/lib/api/types";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ caseId: string }> };

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<NextResponse> {
  try {
    const { caseId } = await context.params;
    let body = {};
    try {
      body = await request.json();
    } catch {
      /* body opcional */
    }
    const data = await assignCase(caseId, body);
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message, code: error.code },
        { status: error.status },
      );
    }
    return NextResponse.json(
      { detail: "Error interno del BFF al asignar caso", code: "BFF_ERROR" },
      { status: 500 },
    );
  }
}
