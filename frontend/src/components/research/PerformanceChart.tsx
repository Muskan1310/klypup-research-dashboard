import type { CompanyCard } from "@/lib/types";

/**
 * A hand-rolled bar chart, not a charting library — the data we actually
 * have per company is a single day's price + change_percent (Alpha
 * Vantage's GLOBAL_QUOTE + OVERVIEW, see app/agents/tools/market_data.py),
 * not a historical time series, so this deliberately doesn't claim to be
 * a price-over-time line chart. A real multi-day series would mean a
 * third Alpha Vantage call per ticker on an already-tight free tier (25
 * req/day, 5/min — see backend/.env.example), which this project has
 * already hit real quota limits on; a bar comparing today's % move across
 * the queried companies is honest about what data backs it and adds zero
 * additional API cost, since it's the same change_percent already
 * rendered on each CompanyCard.
 */
export function PerformanceChart({ cards }: { cards: CompanyCard[] }) {
  const withChange = cards.filter(
    (c): c is CompanyCard & { change_percent: number } => c.change_percent !== null
  );
  if (withChange.length === 0) return null;

  const maxAbs = Math.max(...withChange.map((c) => Math.abs(c.change_percent)), 1);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
        Today&apos;s performance
      </h3>
      <div className="mt-3 space-y-2.5">
        {withChange.map((card) => {
          const positive = card.change_percent >= 0;
          const widthPct = (Math.abs(card.change_percent) / maxAbs) * 100;
          return (
            <div key={card.ticker} className="flex items-center gap-3 text-xs">
              <span className="w-14 flex-none font-medium text-slate-700 dark:text-slate-200">
                {card.ticker}
              </span>
              <div className="relative h-4 flex-1 overflow-hidden rounded bg-slate-100 dark:bg-white/5">
                <div
                  className={`h-full rounded ${positive ? "bg-emerald-500" : "bg-rose-500"}`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
              <span
                className={`w-16 flex-none text-right font-medium ${
                  positive
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-rose-600 dark:text-rose-400"
                }`}
              >
                {positive ? "+" : ""}
                {card.change_percent.toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
