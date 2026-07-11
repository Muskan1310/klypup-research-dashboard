# Klypup Investment Research Dashboard

AI-orchestrated, source-attributed investment research — an agent decides which
data sources (stock data, news, SEC filings) a query needs, fetches them in
parallel, and synthesizes a structured, cited report.

Design docs: [`docs/PDD.md`](docs/PDD.md) (product) and [`docs/TDD.md`](docs/TDD.md) (technical).
See `ARCHITECTURE.md` and `DECISIONS.md` (added later) for the final submission-ready versions.

**Status: Milestone 0 — skeleton only.** Auth, AI orchestration, and RAG are not
yet implemented; this milestone proves the frontend/backend/database wiring works.

---

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- Node.js 20+ and [pnpm](https://pnpm.io/installation)
- Docker (for Postgres)
- API keys: [Alpha Vantage](https://www.alphavantage.co/support/#api-key) (free, instant),
  [NewsAPI](https://newsapi.org/register) (free), [Anthropic](https://console.anthropic.com/) (Claude API)

## Setup

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
cp .env.example .env        # then fill in your real keys/secret
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → `{"status": "ok", ...}`

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local
pnpm install
pnpm dev
```

Visit `http://localhost:3000` — it should show the backend health status as `ok`.

---

## Project Structure

```
klypup/
├── backend/       # FastAPI app — see backend/app/ for api/core/agents/rag/models
├── frontend/       # Next.js app (App Router, TypeScript, Tailwind)
├── docs/           # PDD.md, TDD.md — original design documents
├── docker-compose.yml   # Postgres only (see comments in file for why)
└── .gitignore
```

## Known Limitations (Milestone 0)

- No auth, no AI features, no database models yet — coming in subsequent milestones.
- `docker-compose.yml` only runs Postgres; backend/frontend run natively during
  development for faster iteration. Full containerization is a later milestone.
