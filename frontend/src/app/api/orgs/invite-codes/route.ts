import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { BACKEND_URL } from "@/lib/backend";

/** Proxies to FastAPI's POST /orgs/invite-codes — admin-only on the
 * backend (require_role(UserRole.ADMIN)); this route doesn't duplicate
 * that check, it just forwards the request and whatever status the
 * backend actually decides on (201 or 403).
 */
export async function POST(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const backendRes = await fetch(`${BACKEND_URL}/orgs/invite-codes`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await backendRes.json();
  return NextResponse.json(data, { status: backendRes.status });
}
