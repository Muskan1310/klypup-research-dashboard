import { NextRequest, NextResponse } from "next/server";

import { authCookieOptions, AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { BACKEND_URL } from "@/lib/backend";
import type { LoginRequest, TokenResponse } from "@/lib/types";

/**
 * Thin proxy to FastAPI's POST /auth/login. Runs server-side so it can set
 * an httpOnly cookie (see lib/auth-cookie.ts for why) — the access_token
 * itself never reaches the browser's JS-visible response body, only
 * `user`.
 */
export async function POST(request: NextRequest) {
  const body: LoginRequest = await request.json();

  const backendRes = await fetch(`${BACKEND_URL}/auth/login`, {
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
