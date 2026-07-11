"""ReportSource — ties a specific synthesized claim in a report back to the
tool/document it came from. Kept as a first-class table (not nested inside
`structured_result` JSONB) so source attribution is independently queryable
and auditable — e.g. "which reports cited this filing" — per TDD Section 4.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.research_report import ResearchReport


class SourceType(str, enum.Enum):
    STOCK_API = "stock_api"
    NEWS = "news"
    FILING = "filing"


class ReportSource(Base):
    __tablename__ = "report_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("research_reports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(
        SqlEnum(SourceType, name="source_type", native_enum=True), nullable=False
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)

    report: Mapped["ResearchReport"] = relationship(back_populates="sources")
