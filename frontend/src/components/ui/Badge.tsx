import type { Sentiment, SourceType } from "@/lib/types";

const SENTIMENT_CLASSES: Record<Sentiment, string> = {
  // Color-coded per the task spec: green/red/gray for positive/negative/neutral.
  positive: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-900/30 dark:text-emerald-300 dark:ring-emerald-400/20",
  negative: "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20 dark:bg-rose-900/30 dark:text-rose-300 dark:ring-rose-400/20",
  neutral: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-500/15 dark:bg-white/10 dark:text-slate-300 dark:ring-white/10",
};

export function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${SENTIMENT_CLASSES[sentiment]}`}
    >
      {sentiment}
    </span>
  );
}

const SOURCE_TYPE_LABEL: Record<SourceType, string> = {
  stock_api: "Stock data",
  news: "News",
  filing: "Filing",
};

const SOURCE_TYPE_CLASSES: Record<SourceType, string> = {
  stock_api: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20 dark:bg-sky-900/30 dark:text-sky-300 dark:ring-sky-400/20",
  news: "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-900/30 dark:text-amber-300 dark:ring-amber-400/20",
  filing: "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-600/20 dark:bg-brand-900/30 dark:text-brand-300 dark:ring-brand-400/20",
};

export function SourceTypeBadge({ sourceType }: { sourceType: SourceType }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${SOURCE_TYPE_CLASSES[sourceType]}`}
    >
      {SOURCE_TYPE_LABEL[sourceType]}
    </span>
  );
}
