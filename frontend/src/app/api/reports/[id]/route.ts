import { NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";
import { BACKEND_URL } from "@/lib/backend";
import type { UpdateReportTagsRequest } from "@/lib/types";

/** Proxies to FastAPI's DELETE /reports/{id}. */
export async function DELETE(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { id } = await params;
  const backendRes = await fetch(`${BACKEND_URL}/reports/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (backendRes.status === 204) {
    return new NextResponse(null, { status: 204 });
  }
  const data = await backendRes.json();
  return NextResponse.json(data, { status: backendRes.status });
}

/** Proxies to FastAPI's PATCH /reports/{id} — the report's tags are the
 * one field a user can revise after saving (see UpdateReportTagsRequest).
 */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { id } = await params;
  const body: UpdateReportTagsRequest = await request.json();

  const backendRes = await fetch(`${BACKEND_URL}/reports/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();
  return NextResponse.json(data, { status: backendRes.status });
}
