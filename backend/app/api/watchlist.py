"""Company watchlist routes (PDD F8 / assessment "(recommended)"). Thin
per TDD Section 2 — same pattern as app/api/reports.py.

Every route depends on get_scoped_db, never get_db — watchlist_items is
tenant-owned data (CLAUDE.md hard constraint #3).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.tenancy import CurrentUser, ScopedSession, get_current_user, get_scoped_db
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemResponse, WatchlistResponse
from app.services import watchlist_service

router = APIRouter(tags=["watchlist"])


@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    request: WatchlistItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: ScopedSession = Depends(get_scoped_db),
) -> WatchlistItemResponse:
    item = watchlist_service.add_ticker(db, user_id=current_user.user_id, ticker=request.ticker)
    return WatchlistItemResponse.model_validate(item)


@router.get("", response_model=WatchlistResponse)
def list_watchlist(db: ScopedSession = Depends(get_scoped_db)) -> WatchlistResponse:
    items = watchlist_service.list_items(db)
    return WatchlistResponse(items=[WatchlistItemResponse.model_validate(i) for i in items])


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(item_id: int, db: ScopedSession = Depends(get_scoped_db)) -> None:
    removed = watchlist_service.remove_ticker(db, item_id)
    if not removed:
        # 404, not 403 — same cross-tenant-enumeration reasoning as
        # app/api/reports.py.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")
