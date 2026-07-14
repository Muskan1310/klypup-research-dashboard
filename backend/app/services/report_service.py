"""Business logic for saved research reports (TDD Section 4, Section 5).

Every function here takes a ScopedSession (app.core.tenancy), never a raw
Session — research_reports/report_sources are tenant-owned data (CLAUDE.md
hard constraint #3), and there is no code path here that queries them
unscoped.
"""

from app.core.tenancy import ScopedSession
from app.models.report_source import ReportSource, SourceType
from app.models.research_report import ResearchReport
from app.schemas.research import StructuredResult


def save_report(
    db: ScopedSession, *, created_by_user_id: int, query_text: str, structured_result: StructuredResult
) -> ResearchReport:
    """Persist an already-completed /research result and its sources.

    Each entry in structured_result.sources becomes its own report_sources
    row — TDD Section 4's rationale: source attribution needs to be
    independently queryable ("which reports cited this filing"), not just
    nested inside the structured_result JSONB blob. Written in the same
    request as the report itself so a report is never left without its
    sources.
    """
    report = ResearchReport(
        org_id=db.org_id,
        created_by_user_id=created_by_user_id,
        query_text=query_text,
        structured_result=structured_result.model_dump(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    for source in structured_result.sources:
        db.add(
            ReportSource(
                report_id=report.id,
                source_type=SourceType(source.source_type),
                source_ref=source.source_ref,
                claim_text=source.claim_text,
            )
        )
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: ScopedSession) -> list[ResearchReport]:
    return db.query_scoped(ResearchReport).order_by(ResearchReport.created_at.desc()).all()


def get_report(db: ScopedSession, report_id: int) -> ResearchReport | None:
    """None both when `report_id` doesn't exist at all AND when it belongs
    to a different org — query_scoped's org_id filter makes those two
    cases indistinguishable at the query level, which is exactly the
    point: the route maps None to 404, never 403, so an unauthorized
    caller can't learn whether a given report id exists in someone else's
    org.
    """
    return db.query_scoped(ResearchReport).filter(ResearchReport.id == report_id).first()


def delete_report(db: ScopedSession, report_id: int) -> bool:
    """Returns False (not an exception) when there's nothing this org can
    delete — same 404-not-403 reasoning as get_report; the route maps
    False to 404.
    """
    report = get_report(db, report_id)
    if report is None:
        return False
    db.delete(report)
    db.commit()
    return True


def update_report_tags(db: ScopedSession, report_id: int, tags: list[str]) -> ResearchReport | None:
    """Returns None under the same 404-not-403 reasoning as get_report — the
    route maps None to 404. A report's structured_result is an immutable
    snapshot of a completed AI run (see save_report), so tags are the one
    field on a saved report a user can actually revise after the fact.
    """
    report = get_report(db, report_id)
    if report is None:
        return None
    report.tags = tags
    db.commit()
    db.refresh(report)
    return report
