/**
 * The JWT is stored as an httpOnly cookie, not localStorage — chosen
 * deliberately over the more common localStorage approach:
 *
 * localStorage is readable by any JavaScript running on the page, which
 * means any XSS vulnerability anywhere in the app (a compromised
 * dependency, an unescaped render, a third-party script) can exfiltrate
 * the token directly. An httpOnly cookie is invisible to JS entirely —
 * document.cookie can't read it, and neither can an attacker's injected
 * script. That's a real, meaningful reduction in blast radius for a
 * financial-data product handling a bearer token.
 *
 * The trade-off is architectural, not just a config flag: FastAPI's own
 * /auth/login and /auth/signup return the JWT in the JSON body (unchanged
 * — that contract stays as-is, see app/api/auth.py), and only a
 * server-side context can set an httpOnly cookie in the first place (by
 * definition, client JS cannot). So the Next.js Route Handlers under
 * src/app/api/ act as a thin BFF: they call FastAPI, receive the token in
 * the response body, and re-issue it to the browser as an httpOnly
 * cookie on this origin. Every subsequent authenticated call (e.g.
 * /research) goes through another same-origin Route Handler that reads
 * the cookie server-side and attaches it as `Authorization: Bearer …` when
 * calling FastAPI — the browser itself never holds a readable copy of the
 * token or attaches the header directly.
 */

export const AUTH_COOKIE_NAME = "klypup_token";

// Mirrors backend's JWT lifetime (app/core/config.py: jwt_expire_minutes,
// currently 24h) so the cookie doesn't outlive the token it holds. This is
// a deliberately duplicated constant, not derived from the backend at
// runtime — there's no shared-config mechanism between the two projects
// yet, and one is out of scope here.
const JWT_LIFETIME_SECONDS = 60 * 60 * 24;

export function authCookieOptions() {
  return {
    httpOnly: true,
    // Secure requires HTTPS; disabled outside production so local dev
    // (plain http://localhost) still works.
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: JWT_LIFETIME_SECONDS,
  };
}
