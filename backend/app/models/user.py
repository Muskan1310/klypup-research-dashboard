"""User + role.

`role` is a Python enum mapped through SQLAlchemy's Enum type, which creates
a native Postgres ENUM column rather than a plain string. This means invalid
role values are rejected at the database level, not just by application
code — important because `role` is also embedded as a JWT claim and drives
RBAC decisions (TDD Section 9), so it deserves the same "structural, not
conventional" enforcement as org_id scoping.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.invite_code import InviteCode
    from app.models.organization import Organization
    from app.models.research_report import ResearchReport
    from app.models.watchlist_item import WatchlistItem


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role", native_enum=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="users")
    research_reports: Mapped[list["ResearchReport"]] = relationship(back_populates="created_by")
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="user")
    used_invite_codes: Mapped[list["InviteCode"]] = relationship(back_populates="used_by")
