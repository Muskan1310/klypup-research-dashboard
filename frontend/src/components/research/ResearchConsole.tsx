"use client";

import { useState } from "react";

import { QueryForm } from "@/components/research/QueryForm";
import { type QueryState, ResultsPanel } from "@/components/research/ResultsPanel";
import { extractErrorMessage } from "@/lib/api-error";
import type { ResearchQueryRequest } from "@/lib/types";

export function ResearchConsole() {
  const [state, setState] = useState<QueryState>({ status: "idle" });

  async function handleSubmit(query: string) {
    setState({ status: "loading" });
    try {
      const payload: ResearchQueryRequest = { query };
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        setState({
          status: "error",
          message: extractErrorMessage(
            data,
            res.status === 503
              ? "AI service is temporarily unavailable. Please try again shortly."
              : "Something went wrong running that query."
          ),
        });
        return;
      }

      setState({ status: "success", data, query });
    } catch {
      setState({
        status: "error",
        message: "Couldn't reach the server. Check your connection and try again.",
      });
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
          New research query
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          The agent decides which tools it needs — stock data, news, or filings search — per
          query.
        </p>
      </div>
      <QueryForm onSubmit={handleSubmit} disabled={state.status === "loading"} />
      <ResultsPanel state={state} />
    </div>
  );
}
