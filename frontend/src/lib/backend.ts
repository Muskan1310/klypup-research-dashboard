/**
 * The backend base URL, used only from server-side code (Next.js Route
 * Handlers / middleware) — the browser never calls FastAPI directly (TDD
 * Section 1's hard architectural boundary). Reusing NEXT_PUBLIC_API_URL
 * (already established by the Milestone 0 health-check page) rather than
 * introducing a second, private-only env var for the same value.
 */
export const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
