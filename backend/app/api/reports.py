"""Saved research report routes (TDD Section 4, Section 5). Thin per TDD
Section 2 — parse input, call report_service, map to HTTP.

Every route depends on get_scoped_db, never get_db — research_reports is
tenant-owned data (CLAUDE.md hard constraint #3), and query_scoped() is
the only way any of these queries touch it.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.tenancy import CurrentUser, ScopedSession, get_current_user, get_scoped_db
from app.schemas.report import (
    ReportDetailResponse,
    ReportListItem,
    ReportListResponse,
    SaveReportRequest,
)
from app.services import report_service

router = APIRouter(tags=["reports"])


@router.post("", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED)
def save_report(
    request: SaveReportRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: ScopedSession = Depends(get_scoped_db),
) -> ReportDetailResponse:
    report = report_service.save_report(
        db,
        created_by_user_id=current_user.user_id,
        query_text=request.query_text,
        structured_result=request.structured_result,
    )
    return ReportDetailResponse.model_validate(report)


@router.get("", response_model=ReportListResponse)
def list_reports(db: ScopedSession = Depends(get_scoped_db)) -> ReportListResponse:
    reports = report_service.list_reports(db)
    return ReportListResponse(
        reports=[ReportListItem.model_validate(r) for r in reports], total=len(reports)
    )


@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report(report_id: int, db: ScopedSession = Depends(get_scoped_db)) -> ReportDetailResponse:
    report = report_service.get_report(db, report_id)
    if report is None:
        # 404, not 403: a report belonging to another org must look
        # identical to one that doesn't exist at all, so a caller can't
        # use the status code to confirm a given id exists elsewhere.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportDetailResponse.model_validate(report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, db: ScopedSession = Depends(get_scoped_db)) -> None:
    deleted = report_service.delete_report(db, report_id)
    if not deleted:
        # Same 404-not-403 reasoning as GET /reports/{id} above.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
