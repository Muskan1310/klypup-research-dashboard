import { SourceTypeBadge } from "@/components/ui/Badge";
import type { ReportSource } from "@/lib/types";

/**
 * UX choice for source attribution: a list of claims directly beneath the
 * risk summary paragraph, each tagged with its source type and reference —
 * not hover tooltips, and not inline hyperlinks woven into the prose
 * itself. The schema (app/schemas/research.py) doesn't give us character
 * offsets tying a specific sentence in `risk_summary` to a specific
 * `ReportSource` — `sources` is a parallel list of (claim, type, ref)
 * triples, and `claim_text` is the model's own restatement of a claim, not
 * guaranteed to be a verbatim substring of `risk_summary`. Attempting to
 * fuzzy-match claim text back into the prose to place inline citation
 * markers would be fragile and could mis-attribute a claim to the wrong
 * sentence — worse than being explicit. Listing sources as their own
 * always-visible block keeps every citation visible without hovering
 * (better for scanning/audit, which PDD Section 6 calls out as a
 * requirement: "every synthesized claim must be traceable to a specific
 * source") and never asserts a text-position link the data doesn't back.
 */
export function RiskSummary({
  summary,
  sources,
}: {
  summary: string;
  sources: ReportSource[];
}) {
  if (!summary && sources.length === 0) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Risk summary</h3>
      {summary && (
        <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          {summary}
        </p>
      )}

      {sources.length > 0 && (
        <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 dark:border-white/10">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Sources</p>
          <ul className="space-y-2">
            {sources.map((source, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <SourceTypeBadge sourceType={source.source_type} />
                <span className="text-slate-600 dark:text-slate-300">
                  {source.claim_text}{" "}
                  <span className="text-slate-400 dark:text-slate-500">— {source.source_ref}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
