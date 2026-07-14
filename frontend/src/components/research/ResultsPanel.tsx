import { AgentTrace } from "@/components/research/AgentTrace";
import { SaveReportButton } from "@/components/research/SaveReportButton";
import { StructuredResultView } from "@/components/research/StructuredResultView";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Spinner } from "@/components/ui/Spinner";
import type { ResearchQueryResponse } from "@/lib/types";

export type QueryState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: ResearchQueryResponse; query: string };

export function ResultsPanel({ state }: { state: QueryState }) {
  if (state.status === "idle") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-300 py-16 text-center dark:border-white/15">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-600 dark:bg-brand-400/10 dark:text-brand-300">
          <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
            <path
              fillRule="evenodd"
              d="M9 3.5a5.5 5.5 0 1 0 3.42 9.816l3.132 3.132a.75.75 0 1 0 1.06-1.06l-3.132-3.133A5.5 5.5 0 0 0 9 3.5ZM5 9a4 4 0 1 1 8 0 4 4 0 0 1-8 0Z"
              clipRule="evenodd"
            />
          </svg>
        </span>
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
          No research yet
        </p>
        <p className="max-w-sm text-sm text-slate-400 dark:text-slate-500">
          Ask a question about a company above — the agent will pull live stock data, recent
          news, and filings as needed.
        </p>
      </div>
    );
  }

  if (state.status === "loading") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-slate-200 py-16 text-center dark:border-white/10">
        <Spinner className="h-6 w-6 text-brand-600 dark:text-brand-400" />
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Running the agent — deciding which tools to call, then fetching stock data, news, and
          filings as needed. This can take several seconds.
        </p>
      </div>
    );
  }

  if (state.status === "error") {
    return <ErrorBanner message={state.message} />;
  }

  // status === "success" — but that still covers three distinct backend
  // outcomes (CLAUDE.md constraint #7 / TDD Section 11): a plain-text
  // answer (no tools needed), a validated structured result, or
  // malformed_output (tools ran, but the synthesis call's JSON still
  // didn't validate after the bounded retry). Each gets its own explicit
  // render — never a silent fallback.
  const { data, query } = state;

  if (data.status === "malformed_output") {
    return (
      <div className="space-y-4">
        <AgentTrace toolsCalled={data.tools_called} toolsSkipped={data.tools_skipped} />
        <ErrorBanner
          message={
            data.reason ??
            "The agent gathered data but couldn't produce a well-formed report. Try rephrasing your query."
          }
        />
      </div>
    );
  }

  if (data.answer !== null) {
    return (
      <div className="space-y-4">
        <AgentTrace toolsCalled={data.tools_called} toolsSkipped={data.tools_skipped} />
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm leading-relaxed text-slate-700 dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-300">
          {data.answer}
        </div>
      </div>
    );
  }

  const result = data.structured_result;
  if (!result) {
    // Contract guarantees exactly one of answer/structured_result is set
    // when status is "ok" — this branch exists only so TypeScript (and a
    // future reader) never has to assume that without the code proving it.
    return <ErrorBanner message="The agent returned an unexpected empty response." />;
  }

  return (
    <div className="space-y-4">
      <AgentTrace toolsCalled={data.tools_called} toolsSkipped={data.tools_skipped} />
      <StructuredResultView result={result} />
      <SaveReportButton queryText={query} structuredResult={result} />
    </div>
  );
}
