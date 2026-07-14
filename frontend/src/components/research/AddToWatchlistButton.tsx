"use client";

import { useState } from "react";

import type { WatchlistItemCreate } from "@/lib/types";

type AddState = "idle" | "adding" | "added" | "error";

/** A small client-component island embedded per CompanyCard — kept
 * separate from CompanyCards itself (which stays a plain presentational
 * component usable from Server Components, e.g. the saved-report detail
 * page) rather than converting the whole card grid to a client component
 * just for this one button.
 */
export function AddToWatchlistButton({ ticker }: { ticker: string }) {
  const [state, setState] = useState<AddState>("idle");

  async function handleAdd() {
    setState("adding");
    try {
      const payload: WatchlistItemCreate = { ticker };
      const res = await fetch("/api/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setState(res.ok ? "added" : "error");
    } catch {
      setState("error");
    }
  }

  if (state === "added") {
    return <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">On watchlist</span>;
  }

  return (
    <button
      type="button"
      onClick={handleAdd}
      disabled={state === "adding"}
      className="text-xs font-medium text-brand-600 hover:text-brand-500 disabled:opacity-50 dark:text-brand-400 dark:hover:text-brand-300"
    >
      {state === "adding" ? "Adding…" : state === "error" ? "Couldn't add — retry" : "+ Watchlist"}
    </button>
  );
}
