import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME } from "@/lib/auth-cookie";

/** Reads the httpOnly auth cookie from a Server Component (via next/headers
 * — distinct from the NextRequest.cookies API the Route Handlers under
 * src/app/api/ use, same underlying cookie). Server Components that only
 * need to *read* backend data (history list/detail) call the backend
 * directly with this token rather than round-tripping through their own
 * /api/* route handlers — they're already a trusted server context, so
 * there's nothing the proxy layer would add.
 */
export async function getAuthToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(AUTH_COOKIE_NAME)?.value ?? null;
}

export interface CurrentUserClaims {
  userId: number;
  orgId: number;
  role: "admin" | "analyst";
}

/** Reads user_id/org_id/role directly off the JWT's own payload — the same
 * three claims app/core/security.py encodes at login (see
 * create_access_token). Deliberately NOT signature-verified here: this is
 * used only to decide what to *render* (e.g. hide an admin-only button
 * from an analyst), never to decide what to *allow* — the real
 * enforcement is the backend's own get_current_user/require_role
 * dependencies, which do verify the signature, on every actual request.
 * A tampered token could at worst make a button appear that the backend
 * would still reject with a 403 the moment it's used.
 */
export async function getCurrentUser(): Promise<CurrentUserClaims | null> {
  const token = await getAuthToken();
  if (!token) return null;

  const payloadSegment = token.split(".")[1];
  if (!payloadSegment) return null;

  try {
    const payload = JSON.parse(Buffer.from(payloadSegment, "base64url").toString("utf-8"));
    if (!payload.sub || !payload.org_id || !payload.role) return null;
    return { userId: Number(payload.sub), orgId: Number(payload.org_id), role: payload.role };
  } catch {
    return null;
  }
}
