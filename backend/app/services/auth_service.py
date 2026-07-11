"""Business logic for signup/login (TDD Section 5, Section 9).

Kept out of the API layer per TDD Section 2 ("routes thin, business logic
in services"). These functions take a plain `Session` (from `get_db`), not
a `ScopedSession` (from `get_scoped_db`) — deliberately, not as an
oversight: there is no authenticated tenant to scope by yet. Signup is how
a user *gets* an org_id in the first place, and login is how they prove
identity before anything can be scoped to them. Every other tenant-owned
read/write in this codebase should go through `get_scoped_db`
(`app.core.tenancy`); this module is the one legitimate exception to that
rule, for the reason stated above.
"""

from sqlalchemy.orm import Session

from app.core.database import naive_utcnow
from app.core.security import hash_password, verify_password
from app.models.invite_code import InviteCode
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import SignupRequest


class AuthServiceError(Exception):
    """Base class for signup/login failures; the (future) API layer is
    expected to catch these and translate them into HTTP responses."""


class EmailAlreadyRegisteredError(AuthServiceError):
    """Signup attempted with an email that's already in use."""


class InviteCodeNotFoundError(AuthServiceError):
    """No invite code matches what was provided."""


class InviteCodeExpiredError(AuthServiceError):
    """Invite code exists but is past its expires_at."""


class InviteCodeAlreadyUsedError(AuthServiceError):
    """Invite code exists but has already been redeemed by another user."""


class InvalidCredentialsError(AuthServiceError):
    """Login failed. Deliberately generic — see `authenticate()`."""


def signup(db: Session, request: SignupRequest) -> User:
    """Create a new user, either founding a new org (no invite code) or
    joining an existing one (valid invite code). Both paths are one
    transaction: org+admin-user together, or user+invite-code-redemption
    together — never a partial result if something fails mid-way.

    `request.org_name` is guaranteed non-empty here whenever
    `org_invite_code` is falsy — `SignupRequest`'s model validator
    (app/schemas/auth.py) already enforced that before this function was
    ever called.
    """
    if db.query(User).filter(User.email == request.email).first() is not None:
        raise EmailAlreadyRegisteredError(f"{request.email} is already registered")

    hashed_password = hash_password(request.password)

    try:
        if not request.org_invite_code:
            org = Organization(name=request.org_name)
            db.add(org)
            db.flush()  # assigns org.id without ending the transaction

            user = User(
                org_id=org.id,
                email=request.email,
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
            )
            db.add(user)
        else:
            invite = (
                db.query(InviteCode).filter(InviteCode.code == request.org_invite_code).first()
            )
            if invite is None:
                raise InviteCodeNotFoundError("Invite code not found")
            if invite.used_by_user_id is not None:
                raise InviteCodeAlreadyUsedError("Invite code has already been used")
            if invite.expires_at < naive_utcnow():
                raise InviteCodeExpiredError("Invite code has expired")

            user = User(
                org_id=invite.org_id,
                email=request.email,
                hashed_password=hashed_password,
                role=UserRole.ANALYST,
            )
            db.add(user)
            db.flush()  # assigns user.id
            invite.used_by_user_id = user.id

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """Verify a login attempt.

    Raises `InvalidCredentialsError` for BOTH "no such user" and "wrong
    password" — never distinguishing the two, in the exception type,
    message, or anything the caller could branch on. This is the standard
    mitigation against user enumeration: if "no such user" produced a
    different error than "wrong password", an attacker could use the login
    endpoint to test which emails have accounts on the system, one probe
    at a time, without ever needing to guess a real password.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")
    return user
