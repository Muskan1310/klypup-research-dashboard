"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { extractErrorMessage } from "@/lib/api-error";

type TagState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "error"; message: string };

type DeleteState =
  | { status: "idle" }
  | { status: "confirming" }
  | { status: "deleting" }
  | { status: "error"; message: string };

/** The one thing a user can revise on an already-saved report — its
 * structured_result is an immutable snapshot (see backend
 * UpdateReportTagsRequest) — plus deleting the report entirely.
 */
export function ReportActions({
  reportId,
  initialTags,
}: {
  reportId: number;
  initialTags: string[];
}) {
  const router = useRouter();
  const [tags, setTags] = useState(initialTags);
  const [tagInput, setTagInput] = useState(initialTags.join(", "));
  const [tagState, setTagState] = useState<TagState>({ status: "idle" });
  const [deleteState, setDeleteState] = useState<DeleteState>({ status: "idle" });

  async function handleSaveTags() {
    setTagState({ status: "saving" });
    const parsed = tagInput
      .split(",")
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    const res = await fetch(`/api/reports/${reportId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tags: parsed }),
    });
    const body = await res.json();
    if (!res.ok) {
      setTagState({ status: "error", message: extractErrorMessage(body, "Couldn't save tags.") });
      return;
    }
    setTags(body.tags ?? []);
    setTagInput((body.tags ?? []).join(", "));
    setTagState({ status: "idle" });
  }

  async function handleDelete() {
    setDeleteState({ status: "deleting" });
    const res = await fetch(`/api/reports/${reportId}`, { method: "DELETE" });
    if (res.status === 204) {
      router.push("/dashboard/history");
      return;
    }
    const body = await res.json().catch(() => null);
    setDeleteState({
      status: "error",
      message: extractErrorMessage(body, "Couldn't delete this report."),
    });
  }

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]">
      <div>
        <label
          htmlFor="report-tags"
          className="text-sm font-medium text-slate-700 dark:text-slate-300"
        >
          Tags
        </label>
        <div className="mt-1.5 flex flex-col gap-2 sm:flex-row">
          <input
            id="report-tags"
            value={tagInput}
            onChange={(event) => setTagInput(event.target.value)}
            placeholder="e.g. ev, watchlist, q3-earnings"
            className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-brand-500 dark:border-white/15 dark:bg-white/5 dark:text-white dark:placeholder:text-slate-500"
          />
          <Button
            type="button"
            variant="secondary"
            onClick={handleSaveTags}
            disabled={tagState.status === "saving"}
          >
            {tagState.status === "saving" ? "Saving…" : "Save tags"}
          </Button>
        </div>
        <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">Comma-separated.</p>
        {tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-400/10 dark:text-brand-300"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
        {tagState.status === "error" && (
          <div className="mt-2">
            <ErrorBanner message={tagState.message} />
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 border-t border-slate-100 pt-4 dark:border-white/10">
        {deleteState.status === "confirming" || deleteState.status === "deleting" ? (
          <>
            <span className="text-sm text-slate-600 dark:text-slate-300">Delete this report?</span>
            <Button
              type="button"
              variant="primary"
              className="!bg-rose-600 hover:!bg-rose-500"
              onClick={handleDelete}
              disabled={deleteState.status === "deleting"}
            >
              {deleteState.status === "deleting" ? "Deleting…" : "Confirm delete"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setDeleteState({ status: "idle" })}
              disabled={deleteState.status === "deleting"}
            >
              Cancel
            </Button>
          </>
        ) : (
          <Button
            type="button"
            variant="ghost"
            className="text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:text-rose-400 dark:hover:bg-rose-950/40"
            onClick={() => setDeleteState({ status: "confirming" })}
          >
            Delete report
          </Button>
        )}
        {deleteState.status === "error" && <ErrorBanner message={deleteState.message} />}
      </div>
    </div>
  );
}
