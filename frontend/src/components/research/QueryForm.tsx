"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";

const EXAMPLE_QUERIES = [
  "Give me a quick overview of Tesla",
  "Compare NVIDIA and AMD stock performance",
  "What are AMD's main risk factors?",
];

export function QueryForm({
  onSubmit,
  disabled,
}: {
  onSubmit: (query: string) => void;
  disabled: boolean;
}) {
  const [query, setQuery] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label htmlFor="research-query" className="sr-only">
        Research query
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="research-query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={disabled}
          placeholder="Ask about a company — e.g. “Give me a quick overview of Tesla”"
          className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 shadow-sm shadow-slate-900/[0.02] placeholder:text-slate-400 transition-colors focus:border-brand-500 focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-brand-500 disabled:bg-slate-100 dark:border-white/15 dark:bg-white/5 dark:text-white dark:placeholder:text-slate-500"
        />
        <Button type="submit" disabled={disabled || !query.trim()} className="sm:w-32">
          {disabled ? "Running…" : "Research"}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((example) => (
          <button
            key={example}
            type="button"
            disabled={disabled}
            onClick={() => setQuery(example)}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-50 dark:border-white/10 dark:text-slate-400 dark:hover:border-brand-400/30 dark:hover:bg-brand-400/10 dark:hover:text-brand-300"
          >
            {example}
          </button>
        ))}
      </div>
    </form>
  );
}
