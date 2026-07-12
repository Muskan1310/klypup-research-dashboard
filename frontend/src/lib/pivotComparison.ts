import type { ComparisonRow } from "@/lib/types";

/**
 * Pivots the backend's long/tidy comparison rows (one row per
 * ticker+metric+value — see ComparisonRow in lib/types.ts for why the
 * backend stores it this way) into the wide grid the "Financial Comparison
 * Table" UI (PDD Section 8) actually needs: one column per ticker, one row
 * per metric.
 */
export function pivotComparisonTable(rows: ComparisonRow[]) {
  const tickers: string[] = [];
  const metrics: string[] = [];
  const valueByKey = new Map<string, string>();

  for (const row of rows) {
    if (!tickers.includes(row.ticker)) tickers.push(row.ticker);
    if (!metrics.includes(row.metric)) metrics.push(row.metric);
    valueByKey.set(`${row.metric}::${row.ticker}`, row.value);
  }

  return {
    tickers,
    metrics,
    valueFor: (metric: string, ticker: string) => valueByKey.get(`${metric}::${ticker}`) ?? "—",
  };
}
