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
