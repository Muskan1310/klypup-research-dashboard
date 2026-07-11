"""Business logic for organizations (TDD Section 5).

Org creation itself lives in `auth_service.signup()` for the org-founding
signup path — there's no separate "create org" flow in the current API
contract, since `POST /orgs` (TDD Section 5) is an admin-only route for
generating *additional* invite codes on an org that already exists.
"""

import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.database import naive_utcnow
from app.models.invite_code import InviteCode

INVITE_CODE_EXPIRY = timedelta(days=7)
"""7 days: long enough that an invited analyst who's traveling, or simply
slow to check email, still has a realistic window to accept — short enough
that a forgotten or leaked code doesn't stay redeemable indefinitely. This
product handles financial research access, so we lean toward the tighter
end of common invite-expiry conventions (e.g. GitHub org invites: 7 days)
rather than something like Slack's much longer, lower-sensitivity default.
"""


def create_invite_code(db: Session, org_id: int) -> InviteCode:
    """Generate a single-use invite code for `org_id`.

    The code itself comes from `secrets.token_urlsafe`, not a sequential ID
    or anything derived from guessable state (timestamp, counter) — it must
    be infeasible to enumerate or predict, since possessing a valid code is
    the *only* thing standing between an anonymous signup request and
    membership in someone else's org (CLAUDE.md hard constraint #5: no
    hand-rolled crypto — `secrets` is Python's standard, CSPRNG-backed
    module for exactly this).
    """
    invite = InviteCode(
        org_id=org_id,
        code=secrets.token_urlsafe(32),
        expires_at=naive_utcnow() + INVITE_CODE_EXPIRY,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite
