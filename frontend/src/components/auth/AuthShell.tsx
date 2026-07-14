import type { ReactNode } from "react";

const FEATURES = [
  "An agent that decides which tools a query needs — stock data, news, or filings — and runs them concurrently",
  "Every synthesized claim traced back to a specific source, not just an answer",
  "Hard tenant isolation: your org's research stays your org's",
];

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-full flex-1">
      <div className="relative hidden w-[42%] flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-900 via-brand-700 to-brand-500 px-10 py-12 text-white md:flex">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-32 -left-16 h-80 w-80 rounded-full bg-brand-300/20 blur-3xl"
        />

        <div className="relative flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15 text-sm font-bold backdrop-blur-sm">
            K
          </span>
          <span className="text-lg font-semibold tracking-tight">Klypup Research</span>
        </div>

        <div className="relative space-y-8">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Investment research,
            <br />
            minutes not days.
          </h1>
          <ul className="space-y-4">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-3 text-sm text-brand-50/90">
                <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-white/15 text-[10px] font-bold">
                  ✓
                </span>
                {feature}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-brand-100/60">
          Klypup Applied AI Intern assessment — Option A
        </p>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-12">{children}</div>
    </main>
  );
}
