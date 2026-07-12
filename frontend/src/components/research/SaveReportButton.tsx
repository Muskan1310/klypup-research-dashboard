"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import type { SaveReportRequest, StructuredResult } from "@/lib/types";

type SaveState = "idle" | "saving" | "saved" | "error";

export function SaveReportButton({
  queryText,
  structuredResult,
}: {
  queryText: string;
  structuredResult: StructuredResult;
}) {
  const [state, setState] = useState<SaveState>("idle");

  async function handleSave() {
    setState("saving");
    try {
      const payload: SaveReportRequest = { query_text: queryText, structured_result: structuredResult };
      const res = await fetch("/api/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setState(res.ok ? "saved" : "error");
    } catch {
      setState("error");
    }
  }

  if (state === "saved") {
    return (
      <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
        Saved to history
      </p>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Button variant="secondary" onClick={handleSave} disabled={state === "saving"}>
        {state === "saving" ? "Saving…" : "Save report"}
      </Button>
      {state === "error" && (
        <span className="text-xs text-rose-600 dark:text-rose-400">Couldn&apos;t save. Try again.</span>
      )}
    </div>
  );
}
