# Klypup Investment Research Dashboard — Project Context for Claude Code

This file is read automatically at the start of every Claude Code session in
this repo. It exists to bridge context from design conversations that happened
elsewhere (Claude.ai chat) into your implementation sessions — without it,
you'd make reasonable-but-generic choices that might contradict decisions
already made deliberately, for reasons already argued through and defended.

**Read `docs/PDD.md` and `docs/TDD.md` in full before implementing anything.**
Those are the source of truth for product and technical design. This file is
a summary + a set of hard constraints — it does not replace them.

---

## What this project is

A 5-day take-home technical assessment (Klypup Applied AI Intern). Full-stack
investment research dashboard: a user types a natural-language query, an
LLM-driven agent decides which of 3 tools to call (stock data, news search,
document/filings RAG search), executes them (in parallel where possible),
and synthesizes a structured, source-attributed report. Multi-tenant,
JWT-authed, two roles (Admin/Analyst).

The person building this will have a live CTO interview afterward and must
be able to explain every architectural decision and every non-trivial line
of code. **Optimize for explainability and correctness over cleverness or
line count.** If you (Claude Code) generate something the person couldn't
defend in an interview without your help, it's the wrong choice — favor
the more obvious, more standard approach over a fancier one.

---

## Hard constraints — do not deviate from these without flagging it explicitly

1. **No agent frameworks.** No LangChain, CrewAI, LlamaIndex, or similar.
   Tool-calling orchestration is hand-rolled using the raw Anthropic Python
   SDK's tool-use API directly. This is a deliberate choice for interview
   transparency — every step of the loop must be code the person wrote and
   can point to, not framework internals.

2. **Vector store is Chroma**, running locally/embedded. Not pgvector, not
   Pinecone, not FAISS. This was an explicit, argued decision (see TDD
   Section 8 / Summary table) — don't "improve" it unprompted.

3. **Multi-tenancy is enforced structurally, not by convention.** Every
   tenant-scoped query must go through a `get_scoped_db(current_user)`
   FastAPI dependency (see TDD Section 10) that pre-binds the org filter.
   Never write a raw query with a manually-added `.filter(org_id=...)` in a
   route or service function — that's the exact anti-pattern this project
   is designed to avoid.

4. **`org_id` is derived only from the JWT**, never accepted from a request
   body or query param, anywhere, ever.

5. **Auth is JWT via a well-established library** (`python-jose` + `bcrypt`
   (direct), already in `pyproject.toml`). No hand-rolled crypto. Note:
   `passlib` was dropped — its bcrypt handler is broken against bcrypt>=4.1
   (no fixed passlib release exists), so `app/core/security.py` calls
   `bcrypt.hashpw`/`checkpw` directly instead of going through passlib's
   `CryptContext`.

6. **Database access is synchronous SQLAlchemy** (not async) for Milestone 0–
   most milestones. See `app/core/database.py` comments for why.

7. **Error handling must be explicit, not silent.** Failed tool calls produce
   a structured `{"status": "failed", "reason": ...}` result that gets passed
   to the synthesis step — never swallowed, never a bare `except: pass`.

8. **RAG must include the confidence/quality gate** described in TDD Section
   8 — low-similarity retrieval results must NOT be silently fed to the
   synthesis call as if reliable. This is the project's stated
   differentiator; don't build naive top-k-always-trusted RAG.

9. **The agent's reasoning trace (which tools were called/skipped, and why)
   must be a first-class part of the API response**, not just a log line —
   it's rendered in the UI. See PDD Section 8.

---

## Scope discipline — actively push back on scope creep

This is a 5-day assessment, not a startup runway. If asked to build something
in the PDD's "Future Scope" list (streaming/SSE, PDF/CSV export, >2 roles,
multi-LLM fallback, scheduled watchlist re-runs, pgvector migration) —
**stop and flag it** rather than building it. The person has explicitly
asked to be protected from scope creep. When in doubt, favor the smaller,
more defensible implementation over the more impressive-looking one.

---

## Current status

**Milestone 0 complete**: repo skeleton, FastAPI backend with `/health`,
Next.js frontend rendering that health check, Postgres via Docker Compose.
No auth, no models, no AI logic yet.

**Next up: Milestone 1** — database schema (organizations, users,
research_reports, report_sources, watchlist_items, documents, invite_codes —
see TDD Section 4) and the tenant-scoping dependency. Do not skip ahead to
auth or AI logic until this is done and reviewed.

Milestone order (see TDD/PDD for full detail, don't reorder without discussion):
0. Skeleton ✅ → 1. DB schema + tenant scoping → 2. Auth/RBAC →
3. AI foundations + first tool → 4. Multi-tool + parallel execution →
5. RAG pipeline → 6. Agent trace + structured output → 7. Frontend dashboard →
8. Saved research CRUD/history/watchlist → 9. Resilience/caching →
10. Polish + docs.

---

## Commands

```bash
# Backend (from backend/)
poetry install
poetry run uvicorn app.main:app --reload --port 8000
poetry run pytest
poetry run ruff check .

# Frontend (from frontend/)
pnpm install
pnpm dev
pnpm lint

# Database
docker compose up -d   # from repo root
```

## Conventions

- Backend: routes thin (`api/`), business logic in `services/`, AI logic in
  `agents/` + `rag/` — never inline agent logic inside route handlers.
- All secrets via env vars, documented in `.env.example`, never committed.
- Every new external-facing route needs an explicit loading/error/empty
  state on the frontend — not just a happy path.
