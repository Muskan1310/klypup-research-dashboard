import Link from "next/link";
import { notFound } from "next/navigation";

import { ReportActions } from "@/components/dashboard/ReportActions";
import { StructuredResultView } from "@/components/research/StructuredResultView";
import { BACKEND_URL } from "@/lib/backend";
import { getAuthToken } from "@/lib/server-auth";
import type { ReportDetailResponse } from "@/lib/types";

export default async function SavedReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const token = await getAuthToken();
  const res = await fetch(`${BACKEND_URL}/reports/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  // Backend returns 404 for both "doesn't exist" and "belongs to another
  // org" (app/api/reports.py) — this page can't and shouldn't distinguish
  // those two cases either.
  if (res.status === 404) notFound();
  if (!res.ok) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300">
        Couldn&apos;t load this report. Try refreshing the page.
      </div>
    );
  }

  const report: ReportDetailResponse = await res.json();

  return (
    <div className="space-y-4">
      <div>
        <Link
          href="/dashboard/history"
          className="text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          ← Saved research
        </Link>
        <h1 className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">
          {report.query_text}
        </h1>
      </div>
      <StructuredResultView result={report.structured_result} />
      <ReportActions reportId={report.id} initialTags={report.tags ?? []} />
    </div>
  );
}
