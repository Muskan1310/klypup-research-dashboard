"use client";

import { useState } from "react";

import type { WatchlistItemResponse } from "@/lib/types";

export function WatchlistStrip({ initialItems }: { initialItems: WatchlistItemResponse[] }) {
  const [items, setItems] = useState(initialItems);
  const [removingId, setRemovingId] = useState<number | null>(null);

  async function handleRemove(id: number) {
    setRemovingId(id);
    const res = await fetch(`/api/watchlist/${id}`, { method: "DELETE" });
    if (res.ok) {
      setItems((current) => current.filter((item) => item.id !== id));
    }
    setRemovingId(null);
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Watchlist</h3>

      {items.length === 0 ? (
        <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
          No companies tracked yet — add one from any research result.
        </p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          {items.map((item) => (
            <span
              key={item.id}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 py-1 pl-3 pr-1.5 text-xs font-medium text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
            >
              {item.ticker}
              <button
                type="button"
                onClick={() => handleRemove(item.id)}
                disabled={removingId === item.id}
                aria-label={`Remove ${item.ticker} from watchlist`}
                className="rounded-full px-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 disabled:opacity-50 dark:hover:bg-white/10 dark:hover:text-slate-200"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
