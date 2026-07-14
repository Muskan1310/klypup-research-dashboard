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
framework internals I'd have to explain by reading docs live. I started
on a hand-rolled Anthropic-SDK loop and deliberately moved to LiteLLM so
the provider is a `.env` edit (`LLM_PROVIDER`/`LLM_MODEL`) instead of a
code change — any single provider's outage, deprecation, or free-tier
quota shouldn't be able to take the whole system down, which matters
for a product making live calls to a third party on every request.
LiteLLM normalizes the *request/response shape* across providers; it
does not run the loop — the two-pass planning/synthesis structure, the
`asyncio.gather` concurrency, and the retry-on-invalid-JSON logic are
all still mine.

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
  single-process cache with no cross-instance coherence. The right call
  for a single backend instance; documented as the thing to swap for
  Redis at real multi-instance scale (`docs/TDD.md` Section 12 frames
  this the same way).
- **No search on saved research** — the history list is browse-by-recency
  for this pass; noted inline in the UI itself. Tags exist and are
  editable per-report (`PATCH /reports/{id}`), just not yet used to filter
  the list view.
- **Docker Compose covers Postgres only** — backend/frontend run natively
  for faster hot-reload during active development; full containerization
  is the natural next step for a deployed environment, not something a
  local dev loop needs.
- **No live deployment.** Local only for this submission.

## What would you improve with 2 more weeks?

A real deploy (Railway/Render for the app, managed Postgres) and Redis
for caching would come first — the two items above that are genuinely
"different infrastructure," not more time writing the same kind of code.
After that: retry-with-backoff for transient LLM/API failures (right now
a rate limit or timeout resolves to a clean failure rather than a silent
retry, which is the correct minimum but not the complete story);
streaming the synthesis output over SSE so the UI can show the agent's
plan forming in real time instead of one loading state (named in the PDD
as the ideal, deliberately deferred as bonus scope here); tag/search on
saved research; and a second LLM-as-judge pass specifically checking
claims in `risk_summary` against `sources` for hallucination, since the
current validation only checks *shape* (does the JSON match the schema),
not *faithfulness* (does the risk summary's prose actually match what the
sources say).

## What was the hardest part and how did you solve it?

Two things, and they were connected. First: getting the structured-output
contract right *before* spending real API calls testing it, rather than
iterating live against provider quota. I dry-ran
`litellm.utils.type_to_response_format_param(StructuredResult)` to
confirm the schema actually satisfied strict-mode constraints
(`additionalProperties: false` everywhere) before ever calling the real
API — which mattered a lot given the second thing.

Second: designing around real LLM-provider quota limits rather than
assuming best-case availability. Gemini's free tier caps at 20
requests/day on the model I ended up using, which is a genuine
constraint for a product that calls an LLM on every research query. The
response was architectural, not just defensive: LiteLLM makes the
provider a config value, not a code path, so a quota-exhausted or
degraded provider is a `.env` edit away from being swapped out; and every
LLM-facing failure mode — malformed structured output, a provider error,
a rate limit — resolves to a clean, typed failure state
(`{"status": "malformed_output"}`, a 503 with a generic message) rather
than a crash or a silent retry loop. Verifying this offline first
(mocked tests, dry-run schema checks) meant most of the logic was
already proven correct before it ever needed a real API call to confirm
it.
