"""Import every model here so they all register with `Base.metadata` and
with SQLAlchemy's mapper registry — this is what lets string-based
`relationship()` forward references (e.g. `Mapped["User"]`) resolve
correctly, and it's what Alembic autogenerate scans to detect the full
schema. Import from here (`from app.models import User, ...`), not from
individual model modules.
"""

from app.models.document import Document
from app.models.invite_code import InviteCode
from app.models.organization import Organization
from app.models.report_source import ReportSource, SourceType
from app.models.research_report import ResearchReport
from app.models.user import User, UserRole
from app.models.watchlist_item import WatchlistItem

__all__ = [
    "Organization",
    "User",
    "UserRole",
    "ResearchReport",
    "ReportSource",
    "SourceType",
    "WatchlistItem",
    "Document",
    "InviteCode",
]
