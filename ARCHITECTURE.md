# Architecture

Klypup Investment Research Dashboard — Option A. This is the submission-ready
architecture document (PDF Section 4.2); `docs/TDD.md` is the original,
longer working design doc this was built from and goes deeper on the
reasoning behind each decision (also see [`DECISIONS.md`](DECISIONS.md)).

## 1. System Architecture

```mermaid
graph TB
    Browser["Browser<br/>(React client components)"]

    subgraph "Next.js (frontend/)"
        ServerComponents["Server Components<br/>dashboard/history/* — read httpOnly<br/>cookie via next/headers, fetch backend directly"]
        BFF["Route Handlers (BFF)<br/>src/app/api/* — issue/read the httpOnly<br/>cookie, attach Bearer token to backend calls"]
        Proxy["proxy.ts<br/>presence-only route guard"]
    end

    subgraph "FastAPI (backend/)"
        Routes["api/ — auth, orgs, research,<br/>reports, watchlist — thin route handlers"]
        Tenancy["core/tenancy.py<br/>get_current_user, get_scoped_db"]
        Orchestrator["agents/orchestrator.py<br/>two-pass tool-calling loop + TTL cache"]
        RAG["rag/ — ingest.py, retriever.py"]
        Services["services/ — auth_service,<br/>org_service, report_service"]
    end

    Postgres[("PostgreSQL<br/>organizations, users, research_reports,<br/>report_sources, invite_codes, documents,<br/>watchlist_items")]
    Chroma[("Chroma<br/>embedded, local<br/>filing chunk vectors")]
    AlphaVantage["Alpha Vantage<br/>(market data)"]
    NewsAPI["NewsAPI<br/>(news + sentiment source)"]
    LLM["LLM provider<br/>Anthropic or Gemini, via LiteLLM"]

    Browser -->|"client fetch, same-origin"| BFF
    Browser -->|"page navigation"| ServerComponents
    Browser -.->|"redirect if no cookie"| Proxy
    BFF -->|"Authorization: Bearer <jwt><br/>(never exposed to browser JS)"| Routes
    ServerComponents -->|"Authorization: Bearer <jwt>"| Routes

    Routes --> Tenancy
    Tenancy --> Postgres
    Routes --> Orchestrator
    Routes --> Services
    Services --> Postgres
    Orchestrator --> RAG
    RAG --> Chroma
    Orchestrator -->|"tool calls"| AlphaVantage
    Orchestrator -->|"tool calls"| NewsAPI
    Orchestrator -->|"planning + synthesis calls"| LLM

    classDef external fill:#f4f4f5,stroke:#999
    class AlphaVantage,NewsAPI,LLM external
```

**Boundary that matters most:** the browser never calls the LLM, Alpha
Vantage, NewsAPI, or Chroma directly — only same-origin Next.js routes,
which either proxy to FastAPI (BFF pattern, for anything needing the
httpOnly-cookie token) or FastAPI itself does the external calls
server-side. API keys never reach client-side JS.

## 2. Data Flow — "Give me a quick overview of Tesla"

```mermaid
sequenceDiagram
    participant U as Browser
    participant N as Next.js BFF<br/>(/api/research)
    participant F as FastAPI<br/>(POST /research)
    participant T as core.tenancy<br/>get_current_user
    participant O as orchestrator.py
    participant Tool as Tools (parallel)
    participant L as LLM (LiteLLM)
    participant D as Postgres

    U->>N: POST /api/research {query}<br/>(httpOnly cookie sent automatically)
    N->>F: POST /research {query}<br/>Authorization: Bearer <jwt>
    F->>T: get_current_user(token)
    T-->>F: CurrentUser(user_id, org_id, role)<br/>or 401 if invalid/expired
    F->>O: run_research_query(query)
    O->>O: cache check (normalized query, 15min TTL)<br/>— miss, continue
    O->>L: Pass 1: planning call + tool schemas
    L-->>O: tool_calls: [get_stock_data(TSLA),<br/>search_news(Tesla)]
    O->>Tool: asyncio.gather(...) — both run concurrently
    Tool-->>O: stock result, news result<br/>(each independently may be {"status":"failed",...})
    O->>L: Pass 2: synthesis call,<br/>response_format=StructuredResult
    L-->>O: JSON
    O->>O: validate against StructuredResult<br/>(1 bounded retry on failure)
    O-->>F: {status, structured_result, tools_called, tools_skipped}
    F-->>N: ResearchQueryResponse (200) or 503 on LLM failure
    N-->>U: same JSON (token never included)
    U->>U: render company card, news, risk summary

    Note over U,D: If the user clicks "Save report":
    U->>N: POST /api/reports {query_text, structured_result}
    N->>F: POST /reports, Bearer token
    F->>T: get_scoped_db(current_user)
    T-->>F: ScopedSession bound to current_user.org_id
    F->>D: INSERT research_reports (org_id=...)<br/>INSERT report_sources (per source)
    D-->>F: report row
    F-->>N: 201 ReportDetailResponse
    N-->>U: confirmation
```

## 3. Database Schema (ER Diagram)

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : "has"
    ORGANIZATIONS ||--o{ RESEARCH_REPORTS : "owns"
    ORGANIZATIONS ||--o{ WATCHLIST_ITEMS : "owns"
    ORGANIZATIONS ||--o{ INVITE_CODES : "issues"
    USERS ||--o{ RESEARCH_REPORTS : "creates"
    USERS ||--o{ WATCHLIST_ITEMS : "tracks"
    USERS |o--o{ INVITE_CODES : "redeems"
    RESEARCH_REPORTS ||--o{ REPORT_SOURCES : "cites"

    ORGANIZATIONS {
        int id PK
        string name
        datetime created_at
    }
    USERS {
        int id PK
        int org_id FK
        string email UK
        string hashed_password
        enum role "admin | analyst"
        datetime created_at
    }
    INVITE_CODES {
        int id PK
        int org_id FK
        string code UK
        datetime expires_at
        int used_by_user_id FK "nullable"
    }
    RESEARCH_REPORTS {
        int id PK
        int org_id FK "indexed — every tenant-scoped query filters on this"
        int created_by_user_id FK
        text query_text
        jsonb structured_result "variable-shaped AI output"
        array tags "nullable"
        datetime created_at
        datetime updated_at
    }
    REPORT_SOURCES {
        int id PK
        int report_id FK
        enum source_type "stock_api | news | filing"
        text source_ref
        text claim_text
    }
    WATCHLIST_ITEMS {
        int id PK
        int org_id FK
        int user_id FK
        string ticker
        datetime added_at
    }
    DOCUMENTS {
        int id PK
        string company_ticker
        string doc_type
        text source_path
        datetime ingested_at
    }
```

`documents` deliberately has no `org_id` — ingested filings are a shared
knowledge base across tenants, not tenant-owned data. Its actual chunk
vectors live in Chroma, not Postgres; this row is only ingestion metadata
letting a Chroma hit map back to a human-readable source.

`org_id` is indexed on every tenant-owned table specifically because
`ScopedSession.query_scoped()` (Section 5 below) filters on it on every
single query — an unindexed `org_id` would make that filter a sequential
scan under any real data volume.

## 4. AI Orchestration Flow

```mermaid
flowchart TD
    Start(["query: str"]) --> Cache{"Cache hit?<br/>(normalized query, 15min TTL)"}
    Cache -->|"yes"| Return(["return cached result<br/>— no LLM call at all"])
    Cache -->|"no"| KeyCheck{"API key configured?"}
    KeyCheck -->|"no"| Raise(["raise RuntimeError<br/>→ 503 at the route"])
    KeyCheck -->|"yes"| Plan["Pass 1: planning call<br/>litellm.acompletion(tools=ALL_TOOLS)"]
    Plan --> Decide{"tool_calls?"}
    Decide -->|"none"| DirectAnswer(["status=ok, answer=<br/>model's direct text<br/>— cached, returned"])
    Decide -->|"1+"| Gather["asyncio.gather(*tool_calls)<br/>— every call in this turn runs concurrently,<br/>including search_documents via asyncio.to_thread<br/>(sync/CPU-bound Chroma call)"]
    Gather --> Results["tool results collected<br/>(each may be {status: failed, reason} —<br/>one failure never blocks the others)"]
    Results --> Synth["Pass 2: synthesis call<br/>response_format=StructuredResult<br/>(no tools= — two-pass design doesn't<br/>support a third round of tool calls)"]
    Synth --> Validate{"StructuredResult.<br/>model_validate_json()<br/>succeeds?"}
    Validate -->|"yes"| Success(["status=ok, structured_result=...<br/>— cached, returned"])
    Validate -->|"no, attempt 1"| Retry["feed validation error back to<br/>the model, ask for corrected JSON"]
    Retry --> Synth
    Validate -->|"no, attempt 2 (final)"| Fail(["status=malformed_output, reason=...<br/>— NOT cached, so a retry a<br/>moment later gets a fresh attempt"])
```

**Tool discrimination is prompt/schema design, not code logic.** The
planning call doesn't run a hardcoded sequence — each tool's JSON-schema
`description` is written specifically to help the model decide when *not*
to call it (e.g. `search_news`'s description explicitly says "do NOT use
this for stock price... use get_stock_data for that instead"). This is
what `agents/orchestrator.py`'s tool definitions demonstrate directly.

**Three tools, one concurrency mechanism.** `get_stock_data`
(Alpha Vantage) and `search_news` (NewsAPI) are real `async def` I/O.
`search_documents` (Chroma) is synchronous/CPU-bound — dispatched via
`asyncio.to_thread` so it participates in the same `asyncio.gather()` as
the other two without blocking the event loop for its duration.

## 5. Multi-Tenant Data Flow

```mermaid
flowchart LR
    Req["HTTP request<br/>Authorization: Bearer <jwt>"] --> Decode["core.security.decode_access_token()<br/>jose.jwt.decode — signature + expiry checked"]
    Decode -->|"invalid/expired"| R401(["401"])
    Decode -->|"valid"| CU["CurrentUser(user_id, org_id, role)<br/>— org_id/role come ONLY from JWT claims,<br/>never from request body/query param"]
    CU --> Scoped["ScopedSession(session, org_id=current_user.org_id)"]
    Scoped --> Query["route/service calls<br/>scoped_db.query_scoped(Model)"]
    Query --> Filter["query_scoped() applies<br/>.filter(Model.org_id == self.org_id)<br/>BEFORE returning control to the caller —<br/>there is no method that returns an<br/>unfiltered Query for a tenant-owned model"]
    Filter --> DB[("Postgres — only this<br/>org's rows are ever visible")]
```

**The specific anti-pattern this avoids:** a route or service function
manually writing `.filter(org_id=current_user.org_id)` per-query. That
pattern fails silently the moment exactly one call site forgets it, and
nothing catches that at review time — the query still *looks* correct.
`ScopedSession` makes the org filter structural: `query_scoped()` is the
*only* way to get a `Query` for a tenant-owned model through it, so a
route that wants to bypass scoping has to explicitly reach for a raw
`Session` (`get_db`) instead of `get_scoped_db` — a visible, reviewable
choice in a diff, not a silently-missing filter.

**Proven, not just asserted:** `tests/test_tenancy.py` constructs two orgs
and shows a session scoped to org A cannot see org B's rows even when
explicitly queried by primary key. `tests/test_api_reports.py`'s
cross-tenant test goes further — over real HTTP, with a real JWT: org B
gets **404, not 403**, on both `GET` and `DELETE` of org A's report
(`app/api/reports.py`), specifically so a 403 can't itself confirm to an
unauthorized caller that the report exists somewhere else. Then the same
report is shown still fully accessible/deletable by org A, proving the
404s were tenant-scoping and not a broken route.

## 6. API Design

Every route except `/auth/*` and `/health` requires `Authorization: Bearer
<jwt>`. `org_id` is resolved from the token server-side — never accepted
from a request body or query param, anywhere.

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `POST` | `/auth/signup` | none | `{email, password, org_name?, org_invite_code?}` | `201` `{access_token, token_type, user}` |
| `POST` | `/auth/login` | none | `{email, password}` | `200` `{access_token, token_type, user}` or `401` |
| `POST` | `/orgs/invite-codes` | Bearer, **Admin only** | — | `201` `{code, expires_at}` or `403` |
| `POST` | `/research` | Bearer | `{query}` | `200` `ResearchQueryResponse` (bimodal — see Section 4) or `503` on LLM failure |
| `POST` | `/reports` | Bearer | `{query_text, structured_result}` | `201` `ReportDetailResponse` |
| `GET` | `/reports` | Bearer | — | `200` `{reports: [{id, query_text, created_at}], total}` (org-scoped) |
| `GET` | `/reports/{id}` | Bearer | — | `200` full report or `404` (own-org-missing and cross-org both 404) |
| `DELETE` | `/reports/{id}` | Bearer | — | `204` or `404` |
| `POST` | `/watchlist` | Bearer | `{ticker}` | `201` `{id, ticker, added_at}` (dedupes per org) |
| `GET` | `/watchlist` | Bearer | — | `200` `{items: [...]}` (org-scoped) |
| `DELETE` | `/watchlist/{id}` | Bearer | — | `204` or `404` |
| `GET` | `/health` | none | — | `200` `{status, service}` — liveness only, no DB dependency |

Full request/response Pydantic schemas: `backend/app/schemas/`. Live
interactive docs at `http://localhost:8000/docs` (FastAPI's generated
OpenAPI UI) once the backend is running.
