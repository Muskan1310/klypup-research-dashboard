import { NextRequest, NextResponse } from "next/server";

import { authCookieOptions, AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { BACKEND_URL } from "@/lib/backend";
import type { SignupRequest, TokenResponse } from "@/lib/types";

/** Thin proxy to FastAPI's POST /auth/signup — same cookie-issuing pattern
 * as /api/auth/login (see that route and lib/auth-cookie.ts).
 */
export async function POST(request: NextRequest) {
  const body: SignupRequest = await request.json();

  const backendRes = await fetch(`${BACKEND_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();

  if (!backendRes.ok) {
    return NextResponse.json(data, { status: backendRes.status });
  }

  const { access_token, user } = data as TokenResponse;
  const response = NextResponse.json({ user }, { status: backendRes.status });
  response.cookies.set(AUTH_COOKIE_NAME, access_token, authCookieOptions());
  return response;
}
