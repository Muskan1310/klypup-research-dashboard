"""Auth routes (TDD Section 5, Section 9): signup, login.

Thin per TDD Section 2 — parse the request, call the service, map
service-layer exceptions to HTTP responses, issue a JWT. No business logic
here; that all lives in `app.services.auth_service`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(tags=["auth"])


def _issue_token(user: User) -> TokenResponse:
    """Build a TokenResponse for `user`. `user_id`/`org_id`/`role` all come
    from this User row — which the service layer looked up or created
    server-side — never from the request body (CLAUDE.md hard constraint
    #4: org_id is derived only from what's in the database/JWT, never from
    client input).
    """
    access_token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role.value)
    return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = auth_service.signup(db, request)
    except auth_service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (
        auth_service.InviteCodeNotFoundError,
        auth_service.InviteCodeExpiredError,
        auth_service.InviteCodeAlreadyUsedError,
    ) as exc:
        # Each of these three carries its own distinct message from the
        # service layer (not-found vs expired vs already-used) — passing
        # it straight through keeps that one message defined in one place
        # rather than re-stating it here.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _issue_token(user)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = auth_service.authenticate(db, request.email, request.password)
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _issue_token(user)
