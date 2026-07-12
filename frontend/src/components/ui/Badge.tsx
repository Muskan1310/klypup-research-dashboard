import type { Sentiment, SourceType } from "@/lib/types";

const SENTIMENT_CLASSES: Record<Sentiment, string> = {
  // Color-coded per the task spec: green/red/gray for positive/negative/neutral.
  positive: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  negative: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
  neutral: "bg-slate-200 text-slate-700 dark:bg-white/10 dark:text-slate-300",
};

export function SentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${SENTIMENT_CLASSES[sentiment]}`}
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
  stock_api: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  news: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  filing: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
};

export function SourceTypeBadge({ sourceType }: { sourceType: SourceType }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${SOURCE_TYPE_CLASSES[sourceType]}`}
    >
      {SOURCE_TYPE_LABEL[sourceType]}
    </span>
  );
}
