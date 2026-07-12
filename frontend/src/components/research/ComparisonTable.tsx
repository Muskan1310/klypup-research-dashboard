import { pivotComparisonTable } from "@/lib/pivotComparison";
import type { ComparisonRow } from "@/lib/types";

export function ComparisonTable({ rows }: { rows: ComparisonRow[] }) {
  if (rows.length === 0) return null;
  const { tickers, metrics, valueFor } = pivotComparisonTable(rows);

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-white/10">
      <table className="w-full min-w-max text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left dark:border-white/10 dark:bg-white/[0.03]">
            <th className="px-4 py-2.5 font-medium text-slate-500 dark:text-slate-400">Metric</th>
            {tickers.map((ticker) => (
              <th
                key={ticker}
                className="px-4 py-2.5 font-medium text-slate-700 dark:text-slate-200"
              >
                {ticker}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric, i) => (
            <tr
              key={metric}
              className={i % 2 === 1 ? "bg-slate-50/60 dark:bg-white/[0.015]" : undefined}
            >
              <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{metric}</td>
              {tickers.map((ticker) => (
                <td key={ticker} className="px-4 py-2.5 font-medium text-slate-800 dark:text-slate-100">
                  {valueFor(metric, ticker)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
