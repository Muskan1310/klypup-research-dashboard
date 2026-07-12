"""Request/response schemas for the company watchlist (PDD F8 — "Should"
priority in the internal PDD, "(recommended)" in the assessment PDF).
Minimal CRUD, same shape of contract as app/schemas/report.py.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistItemCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)


class WatchlistItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    ticker: str
    added_at: datetime


class WatchlistResponse(BaseModel):
    items: list[WatchlistItemResponse]
