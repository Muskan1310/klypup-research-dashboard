import { AddToWatchlistButton } from "@/components/research/AddToWatchlistButton";
import type { CompanyCard } from "@/lib/types";

function formatPrice(price: number | null) {
  return price === null ? "—" : `$${price.toFixed(2)}`;
}

function ChangeBadge({ changePercent }: { changePercent: number | null }) {
  if (changePercent === null) {
    return <span className="text-sm text-slate-400 dark:text-slate-500">—</span>;
  }
  const positive = changePercent >= 0;
  return (
    <span
      className={`text-sm font-medium ${
        positive
          ? "text-emerald-600 dark:text-emerald-400"
          : "text-rose-600 dark:text-rose-400"
      }`}
    >
      {positive ? "+" : ""}
      {changePercent.toFixed(2)}%
    </span>
  );
}

const METRIC_LABELS: Record<string, string> = {
  pe_ratio: "P/E ratio",
  market_cap: "Market cap",
  eps: "EPS",
  volume: "Volume",
};

function formatMetricValue(key: string, value: number) {
  if (key === "market_cap") {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    return `$${(value / 1e6).toFixed(1)}M`;
  }
  if (key === "volume") return value.toLocaleString();
  return value.toString();
}

export function CompanyCards({ cards }: { cards: CompanyCard[] }) {
  if (cards.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {cards.map((card) => (
        <div
          key={card.ticker}
          className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]"
        >
          <div className="flex items-baseline justify-between">
            <span className="font-semibold text-slate-900 dark:text-white">{card.ticker}</span>
            <ChangeBadge changePercent={card.change_percent} />
          </div>
          <div className="mt-1 flex items-end justify-between">
            <span className="text-2xl font-semibold text-slate-900 dark:text-white">
              {formatPrice(card.price)}
            </span>
            <AddToWatchlistButton ticker={card.ticker} />
          </div>

          {card.key_metrics && (
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-slate-100 pt-3 text-xs dark:border-white/10">
              {Object.entries(card.key_metrics)
                .filter(([, value]) => value !== null && value !== undefined)
                .map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-2">
                    <dt className="text-slate-500 dark:text-slate-400">
                      {METRIC_LABELS[key] ?? key}
                    </dt>
                    <dd className="font-medium text-slate-700 dark:text-slate-200">
                      {formatMetricValue(key, value as number)}
                    </dd>
                  </div>
                ))}
            </dl>
          )}
        </div>
      ))}
    </div>
  );
}
