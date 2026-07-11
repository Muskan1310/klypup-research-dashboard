"""Org-admin routes (TDD Section 5). Currently just invite-code generation;
thin per TDD Section 2 — parse input, call the service, return a response.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenancy import CurrentUser, require_role
from app.models.user import UserRole
from app.schemas.org import InviteCodeResponse
from app.services import org_service

router = APIRouter(tags=["orgs"])


@router.post(
    "/invite-codes", response_model=InviteCodeResponse, status_code=status.HTTP_201_CREATED
)
def create_invite_code(
    current_user: CurrentUser = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> InviteCodeResponse:
    """Generate a new invite code for the current admin's org.

    `org_id` comes only from `current_user` (JWT-derived) — never from the
    request, which is why this route takes no request body at all: there's
    nothing for a client to supply that could smuggle in a different org_id
    (CLAUDE.md hard constraint #4). `require_role(UserRole.ADMIN)` rejects
    non-admins with 403 before this function body ever runs.
    """
    invite = org_service.create_invite_code(db, current_user.org_id)
    return InviteCodeResponse.model_validate(invite)
