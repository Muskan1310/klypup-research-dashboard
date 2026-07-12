import { CompanyCards } from "@/components/research/CompanyCards";
import { ComparisonTable } from "@/components/research/ComparisonTable";
import { NewsList } from "@/components/research/NewsList";
import { PerformanceChart } from "@/components/research/PerformanceChart";
import { RiskSummary } from "@/components/research/RiskSummary";
import type { StructuredResult } from "@/lib/types";

/** Shared between the live query results panel and the saved-report detail
 * view (dashboard/history/[id]) — a saved report is just a StructuredResult
 * snapshot, so both render it identically.
 */
export function StructuredResultView({ result }: { result: StructuredResult }) {
  const isEmpty =
    result.company_cards.length === 0 &&
    !result.comparison_table?.length &&
    result.news_items.length === 0 &&
    !result.risk_summary &&
    result.sources.length === 0;

  if (isEmpty) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 py-10 text-center text-sm text-slate-500 dark:border-white/15 dark:text-slate-400">
        The agent didn&apos;t find anything to report for this query.
      </div>
    );
  }

  return (
    <>
      <CompanyCards cards={result.company_cards} />
      <PerformanceChart cards={result.company_cards} />
      {result.comparison_table && <ComparisonTable rows={result.comparison_table} />}
      <NewsList items={result.news_items} />
      <RiskSummary summary={result.risk_summary} sources={result.sources} />
    </>
  );
}
