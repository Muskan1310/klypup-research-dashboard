/**
 * FastAPI error bodies come in two shapes: a plain HTTPException gives
 * `{"detail": "some string"}` (e.g. 401/403/409/503 from our own `raise
 * HTTPException(...)` calls), while a Pydantic request-validation failure
 * gives `{"detail": [{"loc": [...], "msg": "...", "type": "..."}, ...]}`
 * (422). Both need to become one human-readable string for the UI.
 */
export function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item)
        )
        .join("; ");
    }
  }
  return fallback;
}
