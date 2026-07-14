"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import type { InviteCodeResponse } from "@/lib/types";

type State =
  | { status: "idle" }
  | { status: "generating" }
  | { status: "ok"; invite: InviteCodeResponse }
  | { status: "error"; message: string };

/** Admin-only — the page that renders this already checked the role
 * (see dashboard/page.tsx) before ever including it in the tree. This
 * component doesn't re-check anything; it's the PDD's "Admin ... invites
 * users" capability actually reachable from the product, not just the API.
 */
export function InviteTeammate() {
  const [state, setState] = useState<State>({ status: "idle" });

  async function handleGenerate() {
    setState({ status: "generating" });
    try {
      const res = await fetch("/api/orgs/invite-codes", { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setState({
          status: "error",
          message: res.status === 403 ? "Only admins can generate invite codes." : "Couldn't generate a code — try again.",
        });
        return;
      }
      setState({ status: "ok", invite: data });
    } catch {
      setState({ status: "error", message: "Couldn't reach the server." });
    }
  }

  function formatExpiry(iso: string) {
    const date = new Date(iso);
    return Number.isNaN(date.getTime())
      ? iso
      : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Invite a teammate</h3>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Generate a one-time code — anyone who signs up with it joins your organization as an analyst.
      </p>

      {state.status === "ok" ? (
        <div className="mt-3 rounded-lg bg-brand-50 p-3 dark:bg-brand-400/10">
          <code className="text-sm font-semibold text-brand-700 dark:text-brand-300">{state.invite.code}</code>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Expires {formatExpiry(state.invite.expires_at)}
          </p>
        </div>
      ) : (
        <Button
          variant="secondary"
          className="mt-3"
          onClick={handleGenerate}
          disabled={state.status === "generating"}
        >
          {state.status === "generating" ? "Generating…" : "Generate invite code"}
        </Button>
      )}

      {state.status === "error" && (
        <p className="mt-2 text-xs text-rose-600 dark:text-rose-400">{state.message}</p>
      )}
    </div>
  );
}
