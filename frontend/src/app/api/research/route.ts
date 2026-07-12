import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { BACKEND_URL } from "@/lib/backend";
import type { ResearchQueryRequest } from "@/lib/types";

/**
 * Proxies to FastAPI's POST /research, attaching the httpOnly cookie's
 * token as a Bearer header — the one place client code needs the token
 * "used," and it never leaves the server to do it (see lib/auth-cookie.ts).
 */
export async function POST(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const body: ResearchQueryRequest = await request.json();

  const backendRes = await fetch(`${BACKEND_URL}/research`, {
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
