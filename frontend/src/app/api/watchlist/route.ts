import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { BACKEND_URL } from "@/lib/backend";
import type { WatchlistItemCreate } from "@/lib/types";

/** Proxies to FastAPI's POST /watchlist — same BFF reasoning as
 * /api/reports: a client component (the "Add to watchlist" button) can't
 * read the httpOnly cookie itself.
 */
export async function POST(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const body: WatchlistItemCreate = await request.json();

  const backendRes = await fetch(`${BACKEND_URL}/watchlist`, {
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
