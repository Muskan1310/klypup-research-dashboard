"""Business logic for the company watchlist. Same shape as
report_service.py — every function takes a ScopedSession, never a raw
Session (CLAUDE.md hard constraint #3).

Watchlist items are org-scoped for listing/dedup (shared workspace — if
one analyst already added TSLA, a teammate doesn't get a second, redundant
entry), while still recording which user added each one via user_id.
"""

from app.core.tenancy import ScopedSession
from app.models.watchlist_item import WatchlistItem


def add_ticker(db: ScopedSession, *, user_id: int, ticker: str) -> WatchlistItem:
    normalized = ticker.strip().upper()

    existing = (
        db.query_scoped(WatchlistItem).filter(WatchlistItem.ticker == normalized).first()
    )
    if existing is not None:
        return existing

    item = WatchlistItem(org_id=db.org_id, user_id=user_id, ticker=normalized)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_items(db: ScopedSession) -> list[WatchlistItem]:
    return db.query_scoped(WatchlistItem).order_by(WatchlistItem.added_at.desc()).all()


def remove_ticker(db: ScopedSession, item_id: int) -> bool:
    """Returns False (not an exception) when there's nothing this org can
    remove — same 404-not-403 reasoning as report_service.delete_report.
    """
    item = db.query_scoped(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
