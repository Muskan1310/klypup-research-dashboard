"""Request/response schemas for saved research reports (TDD Section 4,
Section 5).
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


class UpdateReportTagsRequest(BaseModel):
    """The one field on an already-saved report a user can revise —
    structured_result is an immutable snapshot (see SaveReportRequest), so
    'update' here means re-tagging, not re-running or editing the result.
    """

    tags: list[str] = Field(max_length=20)


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
