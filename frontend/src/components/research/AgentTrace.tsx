import type { ToolCallTrace } from "@/lib/types";

const TOOL_LABELS: Record<string, string> = {
  get_stock_data: "Stock data",
  search_news: "News search",
  search_documents: "Filings search",
};

function label(name: string) {
  return TOOL_LABELS[name] ?? name;
}

function durationMs(call: ToolCallTrace) {
  const ms = new Date(call.finished_at).getTime() - new Date(call.started_at).getTime();
  return Number.isFinite(ms) ? ms : null;
}

/**
 * The agent reasoning trace, rendered as a first-class part of the page
 * (CLAUDE.md hard constraint #9 / PDD F11 / PDD Section 8's "Agent plan:
 * called Stock, News. Skipped Filings" line) — not tucked into a
 * dev-tools-only log.
 */
export function AgentTrace({
  toolsCalled,
  toolsSkipped,
}: {
  toolsCalled: ToolCallTrace[];
  toolsSkipped: string[];
}) {
  if (toolsCalled.length === 0 && toolsSkipped.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm dark:border-white/10 dark:bg-white/[0.02]">
      <p className="font-medium text-slate-700 dark:text-slate-300">
        Agent plan:{" "}
        {toolsCalled.length > 0 ? (
          <span className="text-slate-900 dark:text-white">
            called {toolsCalled.map((c) => label(c.name)).join(", ")}
          </span>
        ) : (
          <span className="text-slate-500 dark:text-slate-400">no tools needed</span>
        )}
        {toolsSkipped.length > 0 && (
          <span className="text-slate-500 dark:text-slate-400">
            {" "}
            · skipped {toolsSkipped.map(label).join(", ")}
          </span>
        )}
      </p>

      {toolsCalled.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {toolsCalled.map((call, i) => {
            const ms = durationMs(call);
            const failed =
              call.result && typeof call.result === "object" && "status" in call.result
                ? (call.result as { status?: string }).status === "failed"
                : false;
            return (
              <li key={`${call.name}-${i}`} className="flex items-center gap-2 text-xs">
                <span
                  className={`h-1.5 w-1.5 flex-none rounded-full ${
                    failed ? "bg-rose-500" : "bg-emerald-500"
                  }`}
                />
                <span className="text-slate-600 dark:text-slate-300">{label(call.name)}</span>
                <span className="text-slate-400 dark:text-slate-500">
                  {Object.values(call.input).join(", ")}
                </span>
                {ms !== null && (
                  <span className="ml-auto text-slate-400 dark:text-slate-500">{ms}ms</span>
                )}
                {failed && <span className="text-rose-500">failed</span>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
