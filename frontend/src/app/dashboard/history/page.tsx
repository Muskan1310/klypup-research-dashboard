import Link from "next/link";

import { BACKEND_URL } from "@/lib/backend";
import { getAuthToken } from "@/lib/server-auth";
import type { ReportListResponse } from "@/lib/types";

function formatDate(iso: string) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      });
}

export default async function HistoryPage() {
  const token = await getAuthToken();
  const res = await fetch(`${BACKEND_URL}/reports`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
        Couldn&apos;t load saved reports. Try refreshing the page.
      </div>
    );
  }

  const { reports }: ReportListResponse = await res.json();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-white">Saved research</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Reports your org has saved. Tags and search aren&apos;t built yet — a known
          simplification for this pass.
        </p>
      </div>

      {reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 py-16 text-center dark:border-white/15">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
            No saved reports yet
          </p>
          <p className="max-w-sm text-sm text-slate-400 dark:text-slate-500">
            Run a research query and save the results to see them here.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 dark:divide-white/10 dark:border-white/10">
          {reports.map((report) => (
            <li key={report.id}>
              <Link
                href={`/dashboard/history/${report.id}`}
                className="flex items-center justify-between gap-4 p-4 hover:bg-slate-50 dark:hover:bg-white/[0.03]"
              >
                <span className="truncate text-sm font-medium text-slate-900 dark:text-white">
                  {report.query_text}
                </span>
                <span className="flex-none text-xs text-slate-400 dark:text-slate-500">
                  {formatDate(report.created_at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
