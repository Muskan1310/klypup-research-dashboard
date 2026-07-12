"""
Application entrypoint.

Deliberately minimal for Milestone 0: app instance, CORS (frontend needs
to call this from a different origin during local dev), and a single
health check route to prove the skeleton actually runs end-to-end.

Route modules (auth, research, reports, orgs) get registered here via
`app.include_router(...)` starting Milestone 1 — main.py itself should
never grow route logic directly, only wiring.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.orgs import router as orgs_router
from app.api.reports import router as reports_router
from app.api.research import router as research_router
from app.api.watchlist import router as watchlist_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.include_router(auth_router, prefix="/auth")
app.include_router(orgs_router, prefix="/orgs")
app.include_router(research_router, prefix="/research")
app.include_router(reports_router, prefix="/reports")
app.include_router(watchlist_router, prefix="/watchlist")

# CORS: allow the Next.js dev server to call this API.
# Locked to explicit origins, not "*" — even in an assessment, an open
# CORS policy on an API that will hold JWTs is a bad habit to demonstrate.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """
    Liveness check. No auth, no DB dependency — this endpoint should
    answer even if the database is down, so it's useful for infra-level
    monitoring ("is the process alive") separately from "is the app
    fully functional."
    """
    return {"status": "ok", "service": settings.app_name}
