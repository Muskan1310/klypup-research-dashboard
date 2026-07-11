"""Organization — the tenant boundary. Every row in every other tenant-scoped
table hangs off org_id, either directly or transitively.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.invite_code import InviteCode
    from app.models.research_report import ResearchReport
    from app.models.user import User
    from app.models.watchlist_item import WatchlistItem


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    research_reports: Mapped[list["ResearchReport"]] = relationship(back_populates="organization")
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="organization")
    invite_codes: Mapped[list["InviteCode"]] = relationship(back_populates="organization")
