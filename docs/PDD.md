# Product Design Document (PDD)
## Klypup Investment Research Dashboard — Option A

---

## 1. Product Vision

**One-line vision:** Turn days of manual research-analyst work into minutes of AI-orchestrated, source-attributed analysis — without sacrificing the analyst's trust in the output.

**The problem in plain terms:** A research analyst today opens six browser tabs, a terminal, and a PDF reader to answer one question like "how exposed is NVIDIA to a slowdown in hyperscaler capex." They manually correlate stock data, news sentiment, and filing details, then write up a summary. This is slow, inconsistent across analysts, and the underlying data is often stale by the time the write-up is done.

**What we're building:** Not a chatbot that talks about stocks. A system where a natural-language query triggers an *agent* that decides — per query — which data sources are relevant, pulls them (in parallel where possible), and synthesizes a structured, source-attributed report that renders as real UI (cards, tables, charts), not a wall of markdown.

**Why this matters as a product, not just a feature:** The differentiator isn't "we called an LLM." It's that the system is *honest* — every claim traces to a source, every AI decision is visible, and when a data source fails, the user is told plainly rather than served a hallucinated gap-fill. That honesty is what makes an analyst actually trust and adopt the tool, which is the real business problem (adoption, not novelty).

> **CTO framing:** "The product bet here is that analysts won't trust a black-box AI summary — they need traceability. So I designed the whole system around explainability as a first-class feature, not an afterthought bolted on for the assessment rubric."

---

## 2. Target Users

**Primary user: Research Analyst** (buy-side or sell-side), typically covers 15-30 tickers, produces written research multiple times a week, currently spends the majority of their time on data-gathering rather than judgment/analysis.

**Secondary user: Team Lead / Portfolio Manager**, doesn't do the research themselves but consumes it, cares about consistency across analysts and speed of turnaround, and is the one deciding whether to pay for/adopt a tool like this org-wide.

**Tertiary (system-level) user: Org Admin**, manages who's on the team and their access — for our multi-tenant requirement, this role exists mainly to demonstrate RBAC, but conceptually maps to a real ops need (onboarding/offboarding analysts, controlling costs).

---

## 3. User Personas

**Persona 1 — "Priya, Junior Equity Analyst"**
2 years experience, covers a sector (e.g. semiconductors), spends ~60% of her day gathering data rather than reasoning about it. Wants speed without losing the ability to double-check a claim. Will abandon a tool the first time it confidently states something wrong and she can't find where it came from.

**Persona 2 — "Marcus, Senior PM"**
Doesn't run queries himself often, but reviews saved reports from his team before client conversations. Cares about report *consistency* (two analysts asking about the same company should get comparably structured, comparably reliable answers) and wants a quick skim, not a dense document.

**Persona 3 — "Org Admin / Ops"**
Manages seats, ensures Org A's proprietary research and watchlists never leak to Org B (a competing fund could be using the same platform — this is a hard compliance requirement, not a nice-to-have).

---

## 4. User Journey (Core Flow)

1. Priya logs in → lands on **Dashboard Home**, sees her recent queries, saved reports, and watchlist.
2. She types a natural language query: *"Compare NVIDIA and AMD's latest earnings and summarize competitive risk."*
3. She sees a **loading/progress state** that shows the agent's plan forming (not just a spinner — this is a deliberate product decision, explained in TDD's "AI Orchestration" section).
4. Structured results render: company cards, a financial comparison table, a sentiment-tagged news list, a synthesized risk paragraph — each data point tagged with its source.
5. She **saves** the report, tags it "Q3 Earnings," and it appears in her history.
6. Later, she **searches** her saved research by tag or company name.
7. Separately, Marcus logs into the *same org* and can see Priya's saved report (shared workspace); an analyst at a different org logging in sees none of this — hard tenant isolation.

---

## 5. Functional Requirements

| # | Requirement | Priority |
|---|---|---|
| F1 | User signup/login/logout, JWT-based sessions | Must |
| F2 | Org creation + invite-based joining | Must |
| F3 | Role-based access: Admin vs Analyst | Must |
| F4 | Natural-language research query interface | Must |
| F5 | Agent dynamically selects tools per query (stock data / news / filings) | Must |
| F6 | Structured, source-attributed results rendering | Must |
| F7 | Save / tag / search / delete research reports (CRUD) | Must |
| F8 | Company watchlist | Should |
| F9 | Dashboard home with recent activity | Must |
| F10 | Graceful degradation when a data source fails | Must |
| F11 | Agent reasoning trace visible to user | Should (our differentiator) |
| F12 | Query result caching | Should |

---

## 6. Non-Functional Requirements

- **Isolation:** Zero cross-tenant data leakage, enforced at the query layer, not just the UI.
- **Latency:** A multi-tool query should resolve in single-digit seconds where possible — parallel tool execution is a requirement, not an optimization.
- **Resilience:** No single external API failure should crash the whole request.
- **Explainability:** Every synthesized claim must be traceable to a specific source.
- **Cost-awareness:** Repeated identical queries shouldn't re-trigger full LLM + tool cost.
- **Auditability:** Saved reports must be immutable once saved (or versioned) so a compliance reviewer can trust historical research wasn't silently altered.

---

## 7. User Flows

**Flow A — New Research Query**
Input query → Agent plan (tool selection) → parallel tool execution → synthesis → structured render → optional save.

**Flow B — Saved Research Retrieval**
Dashboard → History/Search → filter by tag/company → open saved report (static, no re-query) → optionally re-run as fresh query.

**Flow C — Org Onboarding**
Admin signs up → creates org → generates invite code/link → Analyst signs up via invite → lands in shared workspace.

**Flow D — Watchlist**
Add ticker from any report view → appears on Dashboard Home → quick "recurring analysis" action re-runs a saved query template against it.

---

## 8. Dashboard Layout (Conceptual)

```
┌─────────────────────────────────────────────┐
│ Top bar: Org name | User | Logout            │
├───────────────┬───────────────────────────────┤
│ Sidebar        │  Main Panel                    │
│ - Dashboard    │  [New Research Query box]       │
│ - History      │  Recent Reports (cards)         │
│ - Watchlist    │  Watchlist quick-access strip    │
│ - Settings     │                                  │
│  (Admin only)  │                                  │
└───────────────┴───────────────────────────────┘
```

**Research Results View:**
```
[Query text + "Agent plan: called Stock, News. Skipped Filings (not relevant)"]
[Company Overview Cards]  [Financial Comparison Table]
[Stock Performance Chart]
[News Sentiment List — tagged pos/neg/neutral, dated]
[Synthesized Risk Summary — each sentence source-tagged]
[Save / Tag / Export buttons]
```

> **CTO framing:** The layout choice to show the *agent's plan* inline, not hidden in a log file, is a deliberate UX decision reflecting the product thesis: trust comes from visibility, not just accuracy.

---

## 9. Core Features (MVP)

1. Auth + multi-tenant orgs + RBAC
2. Natural language query → agentic tool orchestration (stock + news + filings)
3. Structured, source-attributed result rendering
4. Saved research CRUD + search/tag
5. Agent reasoning trace
6. Graceful degradation + basic caching

## Future Scope (explicitly out of scope for the 5-day build, called out in DECISIONS.md)

- Watchlist-triggered recurring/scheduled analysis (cron-based re-runs)
- Real-time streaming of agent output (SSE) — bonus, not core
- Export to PDF/CSV
- Fine-grained RBAC beyond 2 roles (e.g. "read-only viewer")
- Multi-LLM fallback for cost/redundancy
- pgvector migration if document volume grows significantly (see TDD trade-off discussion)

> **Why explicitly separating MVP vs Future Scope matters for the interview:** it directly answers "what would you improve with 2 more weeks" from DECISIONS.md, and shows you scoped deliberately rather than ran out of time accidentally. Scoping discipline is itself a graded signal (see hidden criteria discussion) — showing you *chose* to cut something, not that you failed to finish it.
