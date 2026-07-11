"""WatchlistItem — a ticker an analyst is tracking, scoped to their org."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    added_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="watchlist_items")
    user: Mapped["User"] = relationship(back_populates="watchlist_items")
