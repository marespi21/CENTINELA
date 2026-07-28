import { NextResponse } from "next/server";
import { resolveCase } from "@/lib/api/server";
import { ApiError } from "@/lib/api/types";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ caseId: string }> };

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<NextResponse> {
  try {
    const { caseId } = await context.params;
    const body = await request.json();
    const data = await resolveCase(caseId, body);
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message, code: error.code },
        { status: error.status },
      );
    }
    return NextResponse.json(
      { detail: "Error interno del BFF al resolver caso", code: "BFF_ERROR" },
      { status: 500 },
    );
  }
}
