import Link from "next/link";

import type { ReportListItem } from "@/lib/types";

function formatDate(iso: string) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function RecentReports({ reports }: { reports: ReportListItem[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/[0.03]">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Recent research</h3>
        <Link
          href="/dashboard/history"
          className="text-xs text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
        >
          View all
        </Link>
      </div>

      {reports.length === 0 ? (
        <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
          Nothing saved yet — run a query above and save it to see it here.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {reports.map((report) => (
            <li key={report.id}>
              <Link
                href={`/dashboard/history/${report.id}`}
                className="flex items-center justify-between gap-3 text-xs hover:text-indigo-600 dark:hover:text-indigo-400"
              >
                <span className="truncate text-slate-700 dark:text-slate-200">
                  {report.query_text}
                </span>
                <span className="flex-none text-slate-400 dark:text-slate-500">
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
