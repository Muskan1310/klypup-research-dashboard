"""Structural multi-tenancy enforcement (CLAUDE.md hard constraint #3, TDD
Section 10).

The pattern this project rejects: every service function remembering to
write `.filter(org_id=current_user.org_id)` by hand. That's convention, not
structure — it works until exactly one route forgets it, and nothing catches
that at review time because the query still "looks right."

What this module provides instead: `ScopedSession` is a Session wrapper that
is handed an org_id once, at construction, and its only query entry point
(`query_scoped`) always applies that org_id filter before returning control
to the caller. There is no method on `ScopedSession` that returns an
unfiltered `Query` for a tenant-owned model — a route that wants to bypass
scoping has to explicitly reach for a raw `Session` (`get_db`) instead of
`get_scoped_db`, which is a visible, reviewable choice in a diff rather than
a silently-missing filter.

`org_id` itself only ever comes from the decoded JWT (`get_current_user`,
below) — never from a request body or query param (CLAUDE.md hard
constraint #4).
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Query, Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass(frozen=True)
class CurrentUser:
    """The identity carried by a validated JWT — nothing more. Routes and
    services should treat this as the sole source of truth for "who is
    making this request," not re-derive org_id/role from anywhere else.
    """

    user_id: int
    org_id: int
    role: UserRole


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    """FastAPI dependency: decode/validate the bearer JWT and return the
    identity it carries. Every protected route depends on this (directly or
    via `get_scoped_db`) instead of parsing tokens itself (TDD Section 9).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise credentials_exception from None

    raw_user_id = payload.get("sub")
    raw_org_id = payload.get("org_id")
    raw_role = payload.get("role")
    if raw_user_id is None or raw_org_id is None or raw_role is None:
        raise credentials_exception

    try:
        return CurrentUser(
            user_id=int(raw_user_id), org_id=int(raw_org_id), role=UserRole(raw_role)
        )
    except (ValueError, TypeError):
        raise credentials_exception from None


class ScopedSession:
    """A `Session` wrapper pre-bound to one org_id.

    `query_scoped(Model)` is the *only* way to build a `Query` through this
    object, and it always applies `Model.org_id == self.org_id` before
    handing the query back — including when the caller then adds more
    filters of their own (e.g. `.filter(Model.id == some_id)`), since those
    are chained onto the already-scoped query, not a fresh one. There is no
    `query()` or `unscoped_query()` method here, deliberately: for a
    tenant-owned model, there is no code path through `ScopedSession` that
    skips the org filter.

    Write operations (`add`, `commit`, `rollback`, `refresh`) are thin
    passthroughs to the underlying `Session` — org_id is not auto-injected
    on `add()`. That's a deliberate scope boundary: this class prevents
    *reading* another tenant's rows, which is the catastrophic failure mode
    (cross-tenant data leak); it does not silently rewrite the org_id of
    whatever object a caller constructs. The caller is still responsible for
    setting `org_id=scoped_db.org_id` when constructing a new row.
    """

    def __init__(self, session: Session, org_id: int):
        self._session = session
        self.org_id = org_id

    def query_scoped(self, model: type) -> Query:
        if not hasattr(model, "org_id"):
            raise TypeError(
                f"{model.__name__} has no org_id column — it isn't a tenant-scoped "
                "model. Query it via a plain Session (get_db), not ScopedSession."
            )
        return self._session.query(model).filter(model.org_id == self.org_id)

    def add(self, instance) -> None:
        self._session.add(instance)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def refresh(self, instance) -> None:
        self._session.refresh(instance)


def get_scoped_db(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScopedSession:
    """FastAPI dependency: a Session pre-bound to the requesting user's
    org_id, derived only from their JWT. This is what every tenant-scoped
    route/service should depend on instead of `get_db` — see module
    docstring and the `get_db` vs `get_scoped_db` note in
    `app/core/database.py`.
    """
    return ScopedSession(db, org_id=current_user.org_id)


def require_role(*roles: UserRole):
    """Factory for a FastAPI dependency: requires the current user's role
    to be one of `roles`, on top of already being authenticated. Usage:
    `current_user: CurrentUser = Depends(require_role(UserRole.ADMIN))`.

    Lives here rather than in `app.core.security`, deliberately: it's a
    FastAPI request-time authorization dependency built directly on
    `get_current_user` (uses `Depends`, raises `HTTPException`) — the same
    category of thing as `get_scoped_db` just above, which restricts a
    request by org_id. `require_role` restricts by role; both answer
    "given a validated identity, what is this request allowed to do,"
    which is what this module owns. `security.py` stays a framework-agnostic
    module of crypto/JWT primitives with zero FastAPI imports — worth
    keeping clean in case those functions are ever reused outside a request
    context (e.g. a CLI seed script hashing a password directly).
    """

    def _require_role(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "This action requires one of the following roles: "
                    + ", ".join(role.value for role in roles)
                ),
            )
        return current_user

    return _require_role
