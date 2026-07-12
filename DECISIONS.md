# Decisions

## Which option did you choose and why?

Option A, the Investment Research Dashboard. It's the one where the AI
integration has a genuine reason to exist beyond "wrap an LLM in a chat
box" — a research query naturally decomposes into "which of these three
independent data sources do I actually need, fetch the ones I need
concurrently, and turn heterogeneous results into one structured, cited
answer." That's a real orchestration problem, not a prompt-engineering
exercise, and it's the same shape of problem ("plan → gather → synthesize
→ show your work") I'd want to be asked to defend in an interview.

## Why this tech stack? What alternatives did you consider?

**FastAPI + Postgres + SQLAlchemy**, not because the assessment required
it, but because thin routes / services / models is easy to keep honest
under time pressure, and Pydantic gives request *and* LLM-output
validation from the same library rather than two.

**Next.js App Router**, specifically for Server Components: the saved-
research history/detail pages read the auth cookie and call the backend
directly server-side, no client-exposed data-fetching layer needed for
pages that are just "render what the server already has."

**Chroma over pgvector/Pinecone** — argued explicitly in `docs/TDD.md`
Section 8. Embedded, zero extra infrastructure, and this project has ~4
filing chunks total; pgvector's advantage (one fewer moving part, since
Postgres is already there) doesn't outweigh Chroma's simpler API for a
corpus this small, and Pinecone's free tier is unnecessary network
dependency for local dev.

**Hand-rolled tool-calling loop, LiteLLM only for the provider call
itself** — this is the one I'd defend hardest. No LangChain/CrewAI: the
"agent" is `asyncio.gather` over a few `await` calls and an `if`
statement deciding what to do with the model's response, and I wanted
every line of that to be something I wrote and can point to, not
framework internals I'd have to explain by reading docs live. LiteLLM
was a **mid-project pivot** — it started as a hand-rolled Anthropic-SDK
loop, and I switched to LiteLLM specifically so the provider is a `.env`
edit (`LLM_PROVIDER`/`LLM_MODEL`) instead of a code change, which mattered
in practice: Anthropic credits ran out mid-build, and Gemini's free tier
(20 req/day on the model I ended up on) got exhausted repeatedly during
heavy testing. LiteLLM normalizes the *request/response shape* across
providers; it does not run the loop — the two-pass planning/synthesis
structure, the `asyncio.gather` concurrency, and the retry-on-invalid-JSON
logic are all still mine.

**JWT via `python-jose` + `bcrypt` directly, not `passlib`** — `passlib`
1.7.4 (its last release) has a broken bcrypt-handler self-test against
`bcrypt>=4.1`; it raises on startup regardless of actual password length.
Calling `bcrypt.hashpw`/`checkpw` directly avoids a dead dependency
without hand-rolling any actual cryptography.

## How did you approach multi-tenancy? What pattern did you use and why?

Shared database, shared schema, `org_id` column per tenant-owned table —
the standard early-stage-SaaS starting pattern, not schema-per-tenant or
database-per-tenant (real isolation upgrades, but infrastructure this
project doesn't need).

The part I actually care about defending is *how* it's enforced:
structurally, via `core/tenancy.py`'s `ScopedSession`, not by convention.
`query_scoped(Model)` is the only method that returns a `Query` for a
tenant-owned model, and it always applies `.filter(Model.org_id ==
self.org_id)` before the caller can chain anything else onto it — there is
no method on `ScopedSession` that returns an unfiltered query. A route
that wants to skip scoping has to visibly reach for a raw `Session`
(`get_db`) instead of `get_scoped_db`, which is a reviewable choice in a
diff, not a missing `.filter()` that still looks fine at a glance. `org_id`
itself comes only from the decoded JWT, never from a request body or query
param — the invite-code join flow exists specifically so a client can
never supply their own `org_id` at signup either.

Proven, not just asserted: `tests/test_tenancy.py` shows a session scoped
to org A genuinely cannot see org B's rows, even queried by primary key.
`tests/test_api_reports.py` goes further over real HTTP — org B holding a
**valid** JWT gets `404`, not `403`, on both `GET` and `DELETE` of org A's
report, specifically because a `403` would itself confirm the report
exists in someone else's org.

## How did you design the AI integration? What prompt engineering decisions did you make?

Two-pass, not single-shot: a planning call gets tool definitions and
decides what (if anything) to fetch; the actual fetching is my code, never
the model; a synthesis call gets the results back and produces the final
answer. Tool selection is entirely a function of each tool's JSON-schema
`description` — e.g. `search_news`'s description explicitly says "do NOT
use this for stock price... use get_stock_data for that instead." That's
the actual mechanism by which the agent avoids calling every tool on every
query; it's not hardcoded routing, it's the model reading precise
descriptions and discriminating.

The synthesis call is asked for **structured JSON** matching a Pydantic
schema (`response_format=StructuredResult`) instead of free text —
LiteLLM converts the Pydantic model into a strict JSON-schema constraint
and routes it to the provider's native structured-output mode. I
validated that this schema actually satisfies "strict" mode (no open
`dict[str, Any]` anywhere — e.g. a company-comparison table is a long/tidy
list of `{ticker, metric, value}` rows, not an arbitrary-columns table,
since a wide table has no fixed schema to declare) before ever spending a
real API call testing it.

"The provider claims strict mode" isn't the same guarantee as "the JSON
that came back actually validates," so the response is still validated
server-side (`StructuredResult.model_validate_json()`), with **one**
bounded retry — the validation error is fed back to the model verbatim,
asking for corrected JSON only — before giving up with a clean
`{"status": "malformed_output"}`. Never an unbounded retry loop, never a
crash on bad output, never an unvalidated blob handed to the frontend.

The RAG piece has an explicit confidence gate, which I'd call the single
most deliberate design choice in the AI layer: Chroma's raw distance is
converted to a cosine-similarity-equivalent score (verified empirically
that the collection's embeddings are unit-normalized and its space is
`l2`, not cosine — not assumed), and a below-threshold top match returns
`"no_strong_match"` rather than being handed to the synthesis call as if
it were reliable. Most naive RAG retrieves top-k regardless of relevance
and hopes the model ignores bad context; this makes a weak match produce
an honest "not found" instead of a fabricated-sounding answer built on
irrelevant text.

## What trade-offs did you make given the 5-day timeline?

- **In-process TTL cache, not Redis** — a plain dict with active
  expiry-sweeping and a size cap, not lazy-only eviction, but still a
  single-process cache with no cross-instance coherence. Fine for one
  backend process; documented as the thing to swap for Redis at real
  multi-instance scale (`docs/TDD.md` Section 12 frames this the same
  way).
- **No tag/search filtering on saved research** — the history list is
  read-only browse-by-recency right now; noted inline in the UI itself,
  not hidden.
- **No watchlist API/UI** — the `watchlist_items` table exists in the
  schema (so the multi-tenant/RBAC pattern already covers it structurally
  if it gets built), but there's no route or page yet. The assessment
  marks this "recommended," not required.
- **No stock performance chart** — cards, a pivoted comparison table,
  sentiment-tagged news, and a sourced risk summary are all real
  structured UI; a chart component specifically isn't built yet.
- **Docker Compose covers Postgres only** — backend/frontend run natively
  for faster hot-reload during active development; not containerized
  end-to-end.
- **No live deployment.** Local only.

## What would you improve with 2 more weeks?

Redis for caching and a real deploy (Railway/Render for the app,
managed Postgres) would come first — they're the two items on the list
above that are genuinely "different infrastructure," not "more time
writing the same kind of code" like the chart or watchlist. After that:
retry-with-backoff for transient LLM/API failures (right now a rate limit
or timeout surfaces as a clean failure rather than being silently
retried, which is the correct minimum but not the complete story);
streaming the synthesis output over SSE so the UI can show the agent's
plan forming in real time instead of one loading state (explicitly named
in the PDD as the ideal, explicitly deferred as bonus scope here); and a
second LLM-as-judge pass specifically checking claims in `risk_summary`
against `sources` for hallucination, since the current validation only
checks *shape* (does the JSON match the schema), not *faithfulness* (does
the risk summary's prose actually match what the sources say).

## What was the hardest part and how did you solve it?

Two things, honestly, and they were connected. First: getting the
structured-output contract right *before* spending real API calls
testing it, rather than iterating live against provider quota. I dry-ran
`litellm.utils.type_to_response_format_param(StructuredResult)` to
confirm the schema actually satisfied strict-mode constraints
(`additionalProperties: false` everywhere) before ever calling the real
API — which mattered a lot given the second thing.

Second: Gemini's free-tier daily quota (20 requests/day on the model I
landed on) got exhausted repeatedly during testing, sometimes
mid-verification. The fix wasn't technical, it was procedural — stop and
report rather than silently retrying or switching providers without
saying so, verify things offline (mocked tests, dry-run schema checks)
wherever the real behavior didn't require an actual API round-trip, and
treat "the live demo query didn't run today" as a fact to state plainly
rather than something to route around quietly. The 503-not-crash handling
for LLM failures in `app/api/reports.py` and `orchestrator.py` exists
because of exactly this — I hit real rate-limit errors during
development, not just anticipated them.

A close third: **the actual working directory only had a single commit
covering the first three milestones — everything after that (the RAG
pipeline, the LiteLLM rewrite, structured output, reports CRUD, the
entire frontend) existed only as uncommitted changes** until I caught it
during a self-audit against this assessment's own rubric and went back to
reconstruct a real, honest, incremental commit history grouped by actual
feature boundaries rather than one giant catch-up commit. Worth stating
plainly rather than hiding: it's a real process failure I found and fixed
myself, not something a reviewer stumbled onto.
