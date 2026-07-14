# Technical Design Document (TDD)
## Klypup Investment Research Dashboard — Option A

---

## 1. High-Level Architecture

```
┌─────────────┐     HTTPS/JSON      ┌──────────────────────┐
│  Next.js     │ <-----------------> │  FastAPI Backend      │
│  Frontend    │                     │  (REST API)           │
└─────────────┘                     └───────────┬──────────┘
                                                 │
                       ┌─────────────────────────┼─────────────────────────┐
                       │                          │                          │
                ┌──────▼──────┐          ┌───────▼────────┐        ┌───────▼────────┐
                │ PostgreSQL   │          │  Agent /        │        │  Chroma          │
                │ (relational, │          │  Orchestration  │        │  (vector store,  │
                │  tenant data)│          │  Layer          │        │  filings/docs)   │
                └──────────────┘          └───────┬────────┘        └──────────────────┘
                                                   │
                                    ┌──────────────┼──────────────┐
                             ┌──────▼─────┐ ┌──────▼─────┐ ┌──────▼─────┐
                             │ Market Data │ │ News API    │ │ Anthropic  │
                             │ API (ext.)  │ │ (ext.)      │ │ Claude API │
                             └────────────┘ └────────────┘ └────────────┘
```

**Why this shape:** The frontend never talks to the LLM or external APIs directly (this is a stated hard requirement — "no direct LLM calls from the browser," and it's good practice regardless: API keys must never reach the client, and all tenant-scoping/auth must happen server-side where it can't be bypassed).

The **Agent/Orchestration layer** is a distinct conceptual component inside the backend, not its own microservice. At this scale, splitting it into a separate service would add network hops and deployment complexity with zero benefit — an unnecessary complexity we discussed avoiding. In a real production system at much larger scale, this layer might become an independently scaled service (LLM orchestration is often more CPU/IO-bound and benefits from independent autoscaling from the CRUD API) — worth mentioning as a "how this scales" answer, not something to build now.

> **CTO framing:** "I kept this a modular monolith rather than microservices. At our current scale, microservices would add operational overhead (service discovery, network latency, distributed tracing) without a corresponding benefit. I designed the orchestration layer as a clearly separated module so it *could* be extracted into its own service later without a rewrite — separation of concerns now, physical separation only when scale demands it."

---

## 2. Component Diagram

```
backend/
├── api/               # route handlers (thin controllers)
│   ├── auth.py
│   ├── research.py
│   ├── reports.py
│   └── orgs.py
├── core/
│   ├── security.py     # JWT, password hashing
│   ├── tenancy.py       # scoped-session dependency (tenant enforcement)
│   └── config.py
├── agents/
│   ├── orchestrator.py  # the tool-calling loop
│   ├── tools/
│   │   ├── market_data.py
│   │   ├── news_search.py
│   │   └── document_search.py  # RAG retrieval tool
│   └── synthesis.py     # structuring final output
├── rag/
│   ├── ingest.py        # chunking + embedding pipeline
│   └── retriever.py      # Chroma query wrapper + confidence gate
├── models/               # SQLAlchemy models
├── schemas/              # Pydantic request/response contracts
└── services/              # business logic between routes and models
```

**Why separate `agents/` and `rag/` from `api/`:** Route handlers should stay thin — parsing input, calling a service, returning a response. If agent logic lived inside route functions, it would be untestable in isolation and impossible to reason about without tracing HTTP request handling. This is standard separation-of-concerns, but it matters more here because the agent logic is the part you'll be interrogated on — it needs to be a clean, standalone thing you can point to.

---

## 3. Sequence Diagram — Core Research Query Flow

```
User        Frontend        API (auth/tenant mw)     Orchestrator      Tools (parallel)      Claude API      DB
 |  query      |                    |                       |                 |                  |            |
 |------------>|                    |                       |                 |                  |            |
 |             |----POST /research->|                       |                 |                  |            |
 |             |                    |--verify JWT, scope---->|                 |                  |            |
 |             |                    |--tenant OK------------>|                 |                  |            |
 |             |                    |                        |--plan (ask Claude which tools)---->|            |
 |             |                    |                        |<--tool_use: [stock, news]-----------|            |
 |             |                    |                        |--call stock,news in parallel------->|            |
 |             |                    |                        |<--results (or partial on failure)---|            |
 |             |                    |                        |--send tool results back to Claude-->|            |
 |             |                    |                        |<--final structured synthesis--------|            |
 |             |                    |<--structured JSON------|                 |                  |            |
 |             |<--render cards-----|                        |                 |                  |            |
 |             |                    |                        |--(optional) save report------------------------->|
```

**Why this matters to walk through explicitly with the CTO:** it shows the two-pass nature of tool-calling — the model is called *twice*: once to decide what to fetch, once to synthesize after fetching. This is the actual mechanic of Claude's (and OpenAI's) tool-use API, and being able to draw this from memory is a strong signal you understand the mechanism rather than having copy-pasted an example.

---

## 4. Database Schema (Core Entities)

```
organizations
  id (PK), name, created_at

users
  id (PK), org_id (FK), email, hashed_password, role (enum: admin/analyst), created_at

research_reports
  id (PK), org_id (FK), created_by_user_id (FK), query_text, structured_result (JSONB),
  tags (array or join table), created_at, updated_at

report_sources
  id (PK), report_id (FK), source_type (enum: stock_api/news/filing), source_ref (text/url),
  claim_text (text)   -- ties a specific synthesized claim to its origin

watchlist_items
  id (PK), org_id (FK), user_id (FK), ticker, added_at

documents  (RAG ingestion metadata, actual vectors live in Chroma)
  id (PK), company_ticker, doc_type, source_path, ingested_at

invite_codes
  id (PK), org_id (FK), code, expires_at, used_by_user_id (nullable)
```

**Why `report_sources` as its own table instead of embedding source info inside the JSONB blob only:** Source attribution is a *rubric-graded, explainability-critical* feature. Making it a first-class relational entity (not just nested JSON) means we can query "show me every report that cited this specific filing" or audit source usage — which is exactly the kind of design choice a CTO would probe ("how would you audit which sources get used most"). Storing it only inside JSONB would answer the assessment's literal requirement but not survive that follow-up question.

**Why JSONB for `structured_result`:** The shape of a research report varies (sometimes 2 companies, sometimes 3; sometimes has a chart, sometimes doesn't). Modeling every possible shape as rigid relational columns would mean constant schema migrations for what is fundamentally semi-structured, presentation-oriented data. JSONB in Postgres gives us flexibility without giving up the relational guarantees (foreign keys, tenant scoping) on the surrounding metadata. This is a genuinely common real-world pattern (structured metadata relational, variable payload JSONB) — not a shortcut.

**Alternative considered:** Fully normalized schema for every result type. Rejected — over-engineered for content whose shape is inherently presentation-driven and evolves as the UI evolves; would require migrations every time we tweak how a card renders.

---

## 5. API Contracts (Representative)

```
POST /auth/signup            { email, password, org_invite_code? }  -> { user, token }
POST /auth/login              { email, password }                    -> { user, token }

POST /orgs                    { name }                                 -> { org, invite_code }   [admin]

POST /research                 { query: string }                       -> {
                                                                            plan: { tools_called: [...], tools_skipped: [...] },
                                                                            structured_result: {...},
                                                                            sources: [...],
                                                                            partial_failures: [...]
                                                                          }

GET  /reports?tag=&q=&page=    -> { reports: [...], total }
GET  /reports/{id}             -> { report, sources }
DELETE /reports/{id}           -> 204

POST /watchlist                { ticker }   -> { watchlist_item }
GET  /watchlist                 -> { items: [...] }
```

Every route except `/auth/*` requires `Authorization: Bearer <jwt>`, and every route resolves `org_id` from the token — **never from a request body/query param** (a client-supplied `org_id` would be a trivial tenant-isolation bypass; this is a specific security detail worth stating explicitly in the interview).

---

## 6. AI Pipeline (End-to-End)

1. **Query intake** → raw user text.
2. **Planning call to Claude** with tool definitions (JSON schemas for `get_stock_data`, `search_news`, `search_documents`) — model returns which tool(s) to call and with what arguments, or none if the query doesn't need external data.
3. **Parallel execution** of selected tools (`asyncio.gather`) — this is where independent I/O-bound calls (stock API, news API) genuinely benefit from concurrency; sequential calls here would be a real, avoidable, explainable latency cost.
4. **Result aggregation**, including capturing any tool failures explicitly (not silently dropping them).
5. **Synthesis call to Claude**, passing tool results back as `tool_result` blocks, asking for a structured JSON output matching a defined schema (cards/table/sentiment data).
6. **Validation** of the returned JSON against our expected schema (Pydantic) before it ever reaches the frontend — if the model returns malformed structure, we catch it server-side rather than shipping a broken UI.
7. **Persistence** (if user saves) — snapshot both `structured_result` and `report_sources`.

---

## 7. Tool-Calling Flow (Conceptual, First Principles)

At its core, "tool calling" is not the model *executing* anything — the model only ever outputs text (or in this case, a structured intent to call a function with certain arguments). **We** execute the actual function, and **we** feed the result back in a second message. The illusion of "the AI used a tool" is really: model says "I want to call X with args Y" → our code runs X → our code sends the result back to the model as part of the conversation → model continues reasoning with that new information.

This matters conceptually because it demystifies "agentic" — there's no autonomy beyond a structured request/response loop that we fully control and can log/audit at every step. That controllability is exactly why we hand-rolled this instead of using a framework: every step above is a function you wrote and can point to.

**Decision-relevant point for the query "should the agent call filings search or not":** the tool definitions we give Claude include descriptions written specifically to help it discriminate ("use this only when the user asks about SEC filings, earnings call details, or company fundamentals not available from real-time price data"). Prompt/schema design *is* the mechanism by which we get selective tool use — it's not automatic, it comes from how precisely we describe each tool's purpose.

---

## 8. RAG Pipeline

1. **Ingestion (offline/setup script):** sample filings/reports for 3–5 companies → chunked (target ~500 tokens with ~50 token overlap — small enough for retrieval precision, large enough to retain context; overlap prevents losing meaning at chunk boundaries) → embedded (via an embedding model) → stored in Chroma with metadata (`ticker`, `doc_type`, `source_path`).
2. **Retrieval (runtime, as a tool call):** user query (or a sub-query extracted by the planning step) is embedded → cosine similarity search against Chroma → top-k chunks returned with similarity scores.
3. **Confidence/quality gate (our differentiator):** if the top result's similarity score is below a threshold, we do **not** feed it to the synthesis step as if it were reliable ground truth — instead we explicitly tell the model "no strong match found in knowledge base" so it says so to the user, rather than being handed weak context and asked to make the best of it (which is how RAG systems silently hallucinate).
4. **Attribution:** each retrieved chunk carries its `source_path`/`doc_type` forward into the final `report_sources` entries.

**Why 500-token chunks with overlap, not something else:** Too small (e.g. 100 tokens) and chunks lose enough surrounding context to be individually meaningful (a sentence about "revenue growth" without the paragraph naming which segment). Too large (e.g. 2000 tokens) and a single chunk can span multiple unrelated topics, hurting retrieval precision — you get correctly *ranked* but poorly *targeted* results. ~500 tokens is a common empirical middle ground for financial/document text; the overlap specifically guards against a fact being split exactly across a chunk boundary.

> **CTO framing:** "The quality gate is the detail I'm proudest of. Most naive RAG implementations retrieve top-k regardless of actual relevance and just hope the LLM ignores bad context. I made the system explicitly aware of retrieval confidence, so a weak match produces an honest 'not found' rather than a fabricated-sounding answer built on irrelevant text."

---

## 9. Authentication Flow

Standard JWT bearer flow: password hashed with bcrypt at signup, login issues a short-lived JWT containing `user_id`, `org_id`, `role`. Every protected route depends on a FastAPI dependency that decodes/validates the JWT and injects a `CurrentUser` object — no route manually parses tokens.

**Why JWT over server-side sessions:** stateless, no session store needed, and it naturally carries `org_id`/`role` as claims we can use directly for tenant scoping without an extra DB lookup per request. Trade-off: revocation is harder (can't invalidate a JWT before expiry without a blocklist) — acceptable for an assessment; in production I'd note this and mention short expiry + refresh tokens as the standard mitigation.

**Alternative considered:** OAuth via a third-party provider (Google/GitHub login). Rejected as unnecessary for this assessment — it solves a "don't manage passwords" problem we don't have at this scale, and adds external dependency risk to the login flow, which is exactly the kind of unnecessary complexity to avoid.

---

## 10. Multi-Tenancy Strategy

**Pattern chosen: shared database, shared schema, row-level `org_id` scoping enforced structurally via a FastAPI dependency** — not manually repeated per-query.

Concretely: instead of every service function remembering to add `.filter(org_id=current_user.org_id)`, we provide a `get_scoped_db(current_user)` dependency that returns a query helper/session pre-bound to that tenant, so it becomes structurally awkward to *forget* the filter rather than merely disciplined to remember it. This directly addresses the most common way multi-tenancy claims fail under scrutiny (identified as the single biggest tell in weak submissions).

**Alternatives considered:**
- *Schema-per-tenant* (each org gets its own Postgres schema): stronger isolation guarantee, but adds real operational complexity (migrations must run per-schema, connection management gets harder) — overkill at this scale and for this timeline.
- *Database-per-tenant*: even stronger isolation, but completely inappropriate for an assessment with a handful of demo orgs — this is enterprise-scale infrastructure, not a startup MVP pattern.

**Why shared-schema + row-level is the right MVP choice:** it's the industry-standard starting pattern for early-stage multi-tenant SaaS (cheaper to run, simpler migrations, easy to reason about), with a known, well-understood upgrade path (schema-per-tenant, then DB-per-tenant) if a specific customer later demands hard physical isolation (common in regulated finance — worth mentioning, since this *is* a financial data product).

---

## 11. Error Handling Strategy

- **External API failures:** each tool call wrapped in try/except with a timeout; failure produces a structured `{"status": "failed", "reason": ...}` result rather than an exception bubbling up — the synthesis step is explicitly told which sources failed and asked to note that in the output, rather than silently omitting it (this is the graceful-degradation requirement made concrete).
- **LLM API failures/rate limits:** ~~retry with backoff for transient errors~~ **update, post-implementation:** not built — `POST /research` catches the provider's error and returns a clean 503 immediately, no retry. Retry-with-backoff is real, listed future work (see DECISIONS.md's "what would you improve with 2 more weeks"), not something to claim as already in place. What *is* true as originally planned: the frontend shows "AI service temporarily unavailable" rather than a generic 500 or a crash — that half of this line held.
- **Malformed LLM structured output:** validated against a Pydantic schema before touching the DB or frontend; on failure, one bounded retry asking the model to correct its output format, then a clean failure state if it still doesn't validate.
- **Frontend:** every async data-fetching component has explicit loading/error/empty states — not just a happy path.

---

## 12. Caching Strategy

**What we cache:** results for identical (or near-identical, normalized) queries within a short TTL window (e.g. 15 minutes) — since stock/news data doesn't meaningfully change second-to-second, and repeated identical queries during a demo or from an analyst re-checking a result shouldn't re-trigger full LLM + external API cost.

**What we deliberately don't cache:** the decision of *which tools to call* isn't cached separately from the result — caching at the full-response level is simpler and avoids a subtle bug class where a stale tool-selection gets paired with fresh data.

**Implementation:** a simple in-process or Redis-backed cache keyed on a normalized query string + relevant tickers. Redis is the "if we had more time" answer for multi-instance deployments; in-process is fine and honestly defensible for a single-instance assessment demo.

> **CTO framing:** "Caching here is a cost-control decision, not a performance one — LLM + multiple API calls per query adds up, and a lot of real usage is variations on 'check the same 5 tickers I always check.' I'd want production metrics on cache hit rate before over-investing in a more sophisticated invalidation strategy."

---

## 13. Security Considerations

- Secrets (API keys, JWT signing key) only via environment variables, never committed — `.env.example` documents required vars without values.
- `org_id` is **always** derived from the authenticated JWT, never accepted from client input — closing the most obvious tenant-isolation bypass.
- Input validation on all endpoints via Pydantic schemas (reject malformed/oversized queries before they reach the LLM — also a cost-control measure, since an unbounded query could balloon token usage).
- ~~Rate limiting per user/org on the `/research` endpoint specifically~~ **update, post-implementation:** not built. No rate-limiting middleware exists on any route. The TTL query cache (Section 12) reduces redundant *identical* calls, but that's a cost optimization for repeats, not a rate limit against a single user/org hammering the endpoint with distinct queries — a real gap, worth naming honestly rather than leaving this line standing as if it were shipped.
- Passwords hashed with bcrypt (never stored plaintext, never even logged).

---

## 14. Scalability Considerations

- **Stateless API layer** (JWT-based auth, no server-side session state) means horizontal scaling of the FastAPI service is straightforward — just add instances behind a load balancer.
- **Orchestration layer as a separable module** (see Section 1) means if agent workloads become the bottleneck (likely, since LLM calls are the slow part), it can be extracted into its own scaled service later without restructuring the rest of the app.
- **Database:** row-level tenant scoping scales fine to a large number of tenants on a single Postgres instance up to a real point of pain (heavy write contention, very large orgs) — at that point, schema-per-tenant or sharding by `org_id` become the next steps, not something needed now.
- **Vector store:** Chroma is fine for our demo-scale document set; if the knowledge base grew to millions of chunks across many tenants, a managed/distributed vector DB (Pinecone, or pgvector with proper indexing at scale) would be the natural next step — this is the honest answer to "how would this not work at 100x scale," and it's fine to say so directly rather than pretend the current choice is infinitely scalable.

---

## 15. Cost Optimization Strategy

- **Caching** (Section 12) is the primary lever — avoiding redundant LLM + external API calls for repeated queries.
- **Selective tool calling itself is a cost optimization**, not just an architecture choice — a query that only needs news doesn't pay for a filings search or a stock API round-trip. This is worth stating explicitly: the "agentic" design isn't only about capability, it directly reduces average cost-per-query versus a hardcoded "always call everything" pipeline.
- **Bounded retries** (not unbounded) on malformed output or transient failures — an unbounded retry loop against an LLM API is a real, previously-seen cost incident pattern in production systems.
- **Model choice**: using a cost-appropriate model for planning/tool-selection (which is a simpler decision task) versus a stronger model for final synthesis is a legitimate future optimization worth mentioning as a "if I had more time" item, even if we use one model throughout for the assessment itself.

---

## Summary of Deliberate Trade-offs (for quick interview recall)

| Decision | Chosen | Rejected Alternative | Core Reason |
|---|---|---|---|
| Backend | FastAPI (Python) | Node/Express | AI ecosystem alignment, async I/O for parallel tool calls |
| Tool orchestration | Hand-rolled loop | LangChain/CrewAI | Full transparency, explainability under interview questioning |
| Vector store | Chroma | pgvector | Isolate AI-learning concepts from infra learning; explicit trade-off acknowledged |
| Multi-tenancy | Shared schema + row-level, structurally enforced | Schema/DB-per-tenant | Standard MVP SaaS pattern; clear upgrade path if needed |
| Auth | JWT | Server sessions / OAuth | Stateless scaling, no unnecessary external dependency |
| Caching | Simple TTL cache on full response | No caching / per-tool caching | Cost control with minimal complexity |
