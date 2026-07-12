import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";

const PROTECTED_PREFIXES = ["/dashboard"];
const AUTH_PAGES = ["/login", "/signup"];

/**
 * Presence-only route guard, not the actual security boundary — it just
 * redirects for UX (no flash of a protected page, no dead-end auth pages
 * once logged in). It deliberately does NOT verify the JWT's signature or
 * expiry: doing that here would require sharing JWT_SECRET_KEY with the
 * frontend, a second copy of a backend secret this project has no
 * mechanism to keep in sync. The real enforcement already happens
 * server-side on every actual data request: src/app/api/research/route.ts
 * forwards the cookie as a Bearer token to FastAPI, and
 * app.core.tenancy.get_current_user fully validates it there — an
 * expired/forged cookie fails at that point with a real 401, regardless
 * of what this middleware decided.
 */
export function proxy(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  const isAuthPage = AUTH_PAGES.some((prefix) => pathname.startsWith(prefix));

  if (isProtected && !token) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && token) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/signup"],
};
