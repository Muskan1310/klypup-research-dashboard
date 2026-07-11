"""ResearchReport — the saved output of an agent run.

`structured_result` is JSONB rather than fully normalized columns: report
shape varies (2 vs 3 companies, chart vs no chart, etc.), and that shape is
presentation-driven and will shift as the UI evolves. JSONB keeps the
variable payload flexible while everything around it (org_id,
created_by_user_id, timestamps) stays relational and foreign-keyed, so
tenant scoping and auditability aren't given up — see TDD Section 4.

`tags` uses a Postgres array column rather than a join table — TDD leaves
this open ("array or join table"); a join table would be normalization
without a corresponding need (no tag metadata, no cross-report tag
queries required by the current API contract).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.report_source import ReportSource
    from app.models.user import User


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="research_reports")
    created_by: Mapped["User"] = relationship(back_populates="research_reports")
    sources: Mapped[list["ReportSource"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
