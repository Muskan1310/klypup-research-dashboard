import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { BACKEND_URL } from "@/lib/backend";
import type { SaveReportRequest } from "@/lib/types";

/**
 * Proxies to FastAPI's POST /reports — only POST, since the "Save report"
 * button is a client component and can't read the httpOnly cookie itself
 * (same reasoning as /api/research). Reading reports (list/detail) is done
 * directly from Server Components via lib/server-auth.ts instead — no
 * client interactivity there, so no proxy needed for those.
 */
export async function POST(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const body: SaveReportRequest = await request.json();

  const backendRes = await fetch(`${BACKEND_URL}/reports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();
  return NextResponse.json(data, { status: backendRes.status });
}
