import { NextResponse } from "next/server";

import { authCookieOptions, AUTH_COOKIE_NAME } from "@/lib/auth-cookie";

/** Clears the httpOnly auth cookie. There's no server-side JWT
 * revocation/blocklist (TDD Section 9's documented trade-off of stateless
 * JWTs) — this just makes the browser stop sending the token, it doesn't
 * invalidate it before its natural expiry.
 */
export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(AUTH_COOKIE_NAME, "", { ...authCookieOptions(), maxAge: 0 });
  return response;
}
