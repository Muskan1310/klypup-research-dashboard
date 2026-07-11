"""
Database engine + session factory.

We use SQLAlchemy's classic Session pattern (not the async engine) for
Milestone 0. This is a deliberate simplicity choice: FastAPI supports
async DB access, but async SQLAlchemy adds real complexity (async session
lifecycles, greenlet quirks) for a benefit we don't need yet at this
scale — our bottleneck will be LLM API latency, not DB query latency.
If profiling later showed DB concurrency as a real bottleneck, this is
the file we'd revisit.

`get_db()` is a FastAPI dependency: it's *not* tenant-scoped. Tenant
scoping is a separate, deliberately distinct dependency built in
Milestone 1 (`get_scoped_db`) that wraps this one — keeping "give me a
DB session" and "give me a DB session that can only see my org's rows"
as two clearly separate concerns.
"""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class all ORM models inherit from."""

    pass


def get_db():
    """FastAPI dependency: yields a DB session, guarantees it's closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def naive_utcnow() -> datetime:
    """Current UTC time with tzinfo stripped.

    Our timestamp columns (e.g. `invite_codes.expires_at`) are Postgres
    `TIMESTAMP WITHOUT TIME ZONE`, so values read back via SQLAlchemy come
    back as naive datetimes. Comparing/assigning those against a
    timezone-aware `datetime.now(timezone.utc)` raises
    `TypeError: can't compare offset-naive and offset-aware datetimes` —
    this helper is the one place that conversion happens, so application
    code always works in the same (naive, UTC) convention the DB uses.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
