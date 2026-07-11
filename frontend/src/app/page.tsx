/**
 * Milestone 0 placeholder home page.
 *
 * Its only job right now: prove the frontend can reach the backend's
 * /health endpoint. This is the "does the skeleton actually connect
 * end-to-end" smoke test — everything from Milestone 1 onward builds
 * on top of this same fetch pattern (backend URL from env, no
 * hardcoded localhost sprinkled through the codebase).
 */

async function getBackendHealth() {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${backendUrl}/health`, { cache: "no-store" });
    if (!res.ok) return { status: "unreachable", detail: `HTTP ${res.status}` };
    return await res.json();
  } catch {
    return { status: "unreachable", detail: "backend not running" };
  }
}

export default async function Home() {
  const health = await getBackendHealth();

  return (
    <main className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-md w-full space-y-4 text-center">
        <h1 className="text-2xl font-semibold">Klypup Research Dashboard</h1>
        <p className="text-sm text-gray-500">Milestone 0 — skeleton connectivity check</p>
        <div className="rounded-lg border p-4 text-left text-sm">
          <div className="font-mono">
            <span className="text-gray-500">backend status:</span>{" "}
            <span className={health.status === "ok" ? "text-green-600" : "text-red-600"}>
              {health.status}
            </span>
          </div>
          {health.service && <div className="font-mono text-gray-500">{health.service}</div>}
          {health.detail && <div className="font-mono text-gray-500">{health.detail}</div>}
        </div>
      </div>
    </main>
  );
}
