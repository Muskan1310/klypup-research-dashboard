"""Request/response schemas for saved research reports (TDD Section 4,
Section 5). Minimal CRUD contract — no tag/search filtering yet (task's
explicit, deliberate cut for this pass).
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.research import StructuredResult


class SaveReportRequest(BaseModel):
    """What the frontend posts to persist an already-completed /research
    result — it passes back the StructuredResult it already has, rather
    than the backend re-running the query. Saving is a snapshot of an
    existing result, not a fresh research run.
    """

    query_text: str = Field(min_length=1, max_length=2000)
    structured_result: StructuredResult


class ReportListItem(BaseModel):
    """Deliberately lighter than ReportDetailResponse — a list view has no
    need for the full structured_result JSONB blob per row; that's fetched
    on demand via GET /reports/{id} when a specific report is opened.
    """

    model_config = {"from_attributes": True}

    id: int
    query_text: str
    created_at: datetime


class ReportListResponse(BaseModel):
    reports: list[ReportListItem]
    total: int


class ReportDetailResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    query_text: str
    structured_result: StructuredResult
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime
