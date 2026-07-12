import { SentimentBadge } from "@/components/ui/Badge";
import type { NewsItem } from "@/lib/types";

function formatDate(iso: string) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function NewsList({ items }: { items: NewsItem[] }) {
  if (items.length === 0) return null;

  return (
    <ul className="divide-y divide-slate-100 rounded-xl border border-slate-200 dark:divide-white/10 dark:border-white/10">
      {items.map((item, i) => (
        <li key={`${item.url}-${i}`} className="flex items-start justify-between gap-3 p-4">
          <div className="min-w-0">
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-slate-900 hover:text-indigo-600 dark:text-white dark:hover:text-indigo-400"
            >
              {item.title}
            </a>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {item.source} · {formatDate(item.published_at)}
            </p>
          </div>
          <SentimentBadge sentiment={item.sentiment} />
        </li>
      ))}
    </ul>
  );
}
