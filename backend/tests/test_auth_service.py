"""Tests for app/services/auth_service.py (and the invite-code generation
it depends on, app/services/org_service.py).

Run against the real Postgres from docker-compose, like test_tenancy.py —
password hashing, uniqueness constraints, and FK behavior are all things a
mock session would either fake or miss entirely.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.database import naive_utcnow
from app.core.security import verify_password
from app.models import InviteCode, Organization, User, UserRole
from app.schemas.auth import SignupRequest
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InviteCodeAlreadyUsedError,
    InviteCodeExpiredError,
    authenticate,
    signup,
)
from app.services.org_service import create_invite_code

PASSWORD = "a-fairly-long-passphrase"


def _unique_email(label: str) -> str:
    return f"{label}-{uuid4().hex}@example.com"


def test_signup_without_invite_code_founds_new_org_as_admin(db_session):
    email = _unique_email("founder")
    org_name = f"Founder Org {uuid4().hex}"
    user = None
    try:
        user = signup(db_session, SignupRequest(email=email, password=PASSWORD, org_name=org_name))

        assert user.role == UserRole.ADMIN
        assert user.email == email
        # Password must be hashed, not stored/comparable as plaintext.
        assert user.hashed_password != PASSWORD
        assert verify_password(PASSWORD, user.hashed_password)

        org = db_session.query(Organization).filter(Organization.id == user.org_id).first()
        assert org is not None
        assert org.name == org_name
    finally:
        db_session.query(User).filter(User.email == email).delete(synchronize_session=False)
        if user is not None:
            db_session.query(Organization).filter(Organization.id == user.org_id).delete(
                synchronize_session=False
            )
        db_session.commit()


def test_signup_with_valid_invite_code_joins_org_as_analyst(db_session):
    org = Organization(name="Invite Test Org")
    db_session.add(org)
    db_session.commit()

    invite = create_invite_code(db_session, org.id)
    email = _unique_email("analyst")
    user = None
    try:
        user = signup(db_session, SignupRequest(email=email, password=PASSWORD, org_invite_code=invite.code))

        assert user.role == UserRole.ANALYST
        assert user.org_id == org.id

        db_session.refresh(invite)
        assert invite.used_by_user_id == user.id
    finally:
        db_session.query(User).filter(User.email == email).delete(synchronize_session=False)
        db_session.query(InviteCode).filter(InviteCode.id == invite.id).delete(
            synchronize_session=False
        )
        db_session.query(Organization).filter(Organization.id == org.id).delete(
            synchronize_session=False
        )
        db_session.commit()


def test_signup_with_expired_invite_code_raises(db_session):
    org = Organization(name="Expired Invite Org")
    db_session.add(org)
    db_session.commit()

    expired_invite = InviteCode(
        org_id=org.id,
        code=f"expired-{uuid4().hex}",
        expires_at=naive_utcnow() - timedelta(days=1),
    )
    db_session.add(expired_invite)
    db_session.commit()

    email = _unique_email("too-late")
    try:
        with pytest.raises(InviteCodeExpiredError):
            signup(
                db_session,
                SignupRequest(email=email, password=PASSWORD, org_invite_code=expired_invite.code),
            )
        # No user should have been created on the failed attempt.
        assert db_session.query(User).filter(User.email == email).first() is None
    finally:
        db_session.query(InviteCode).filter(InviteCode.id == expired_invite.id).delete(
            synchronize_session=False
        )
        db_session.query(Organization).filter(Organization.id == org.id).delete(
            synchronize_session=False
        )
        db_session.commit()


def test_signup_with_already_used_invite_code_raises(db_session):
    org = Organization(name="Used Invite Org")
    db_session.add(org)
    db_session.commit()

    invite = create_invite_code(db_session, org.id)
    first_email = _unique_email("first")
    second_email = _unique_email("second")
    first_user = None

    try:
        first_user = signup(
            db_session,
            SignupRequest(email=first_email, password=PASSWORD, org_invite_code=invite.code),
        )

        with pytest.raises(InviteCodeAlreadyUsedError):
            signup(
                db_session,
                SignupRequest(email=second_email, password=PASSWORD, org_invite_code=invite.code),
            )
        # The second signup attempt must not have created a user.
        assert db_session.query(User).filter(User.email == second_email).first() is None
    finally:
        if first_user is not None:
            db_session.query(User).filter(User.id == first_user.id).delete(
                synchronize_session=False
            )
        db_session.query(InviteCode).filter(InviteCode.id == invite.id).delete(
            synchronize_session=False
        )
        db_session.query(Organization).filter(Organization.id == org.id).delete(
            synchronize_session=False
        )
        db_session.commit()


def test_signup_with_duplicate_email_raises(db_session):
    email = _unique_email("dupe")
    first_user = None

    try:
        first_user = signup(
            db_session, SignupRequest(email=email, password=PASSWORD, org_name="Dupe Test Org")
        )

        with pytest.raises(EmailAlreadyRegisteredError):
            signup(
                db_session,
                SignupRequest(
                    email=email, password="a-different-passphrase", org_name="Dupe Test Org 2"
                ),
            )
    finally:
        if first_user is not None:
            db_session.query(User).filter(User.id == first_user.id).delete(
                synchronize_session=False
            )
            db_session.query(Organization).filter(Organization.id == first_user.org_id).delete(
                synchronize_session=False
            )
        db_session.commit()


def test_authenticate_wrong_password_and_missing_user_raise_identical_generic_error(db_session):
    email = _unique_email("login")
    user = None

    try:
        user = signup(
            db_session, SignupRequest(email=email, password=PASSWORD, org_name="Login Test Org")
        )

        with pytest.raises(InvalidCredentialsError) as wrong_password:
            authenticate(db_session, email, "definitely-the-wrong-password")

        with pytest.raises(InvalidCredentialsError) as no_such_user:
            authenticate(db_session, _unique_email("nobody"), "whatever-password")

        # Same exception type AND message for both failure modes — proves
        # the endpoint can't be used to enumerate which emails are
        # registered by comparing error responses.
        assert str(wrong_password.value) == str(no_such_user.value)
    finally:
        if user is not None:
            db_session.query(User).filter(User.id == user.id).delete(synchronize_session=False)
            db_session.query(Organization).filter(Organization.id == user.org_id).delete(
                synchronize_session=False
            )
        db_session.commit()


def test_signup_org_founding_without_org_name_fails_schema_validation():
    """org_name is required when org_invite_code is absent — enforced by
    SignupRequest's own model validator (app/schemas/auth.py), not by
    auth_service.signup(). Constructing the request with a missing org_name
    raises ValidationError before any service or DB code would ever run —
    the same ValidationError FastAPI turns into an HTTP 422 automatically
    for a request body, so this is the equivalent of proving the request
    never reaches the service layer, without needing a live route/TestClient
    (none exists yet at this milestone).
    """
    with pytest.raises(ValidationError):
        SignupRequest(email=_unique_email("no-org-name"), password=PASSWORD)
