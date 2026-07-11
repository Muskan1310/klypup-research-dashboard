"""Password hashing and JWT helpers.

Both use well-established libraries rather than hand-rolled crypto
(CLAUDE.md hard constraint #5): `bcrypt` for hashing, `python-jose` for JWT.

Hashing calls `bcrypt` directly rather than through `passlib`'s
`CryptContext`, which CLAUDE.md originally named alongside it. `passlib`
1.7.4 is the last release that exists on PyPI (no newer one has shipped
since 2020) and its bcrypt handler runs a startup self-test that's broken
against bcrypt>=4.1's stricter 72-byte enforcement — it raises
`ValueError: password cannot be longer than 72 bytes` before ever hashing
anything, regardless of the actual input length. Calling `bcrypt` directly
avoids that broken code path entirely while still using the same
underlying, industry-standard primitive `passlib` itself wraps.

`org_id` and `role` are embedded directly as JWT claims at encode time so
downstream request handling never needs a DB round-trip just to answer
"what org/role is this request for" (TDD Section 9) — that's also what
makes structural tenant scoping in `app.core.tenancy` possible without an
extra query per request.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    # bcrypt operates on bytes and only considers the first 72 bytes of
    # input; our schema caps passwords at 72 *characters*
    # (app/schemas/auth.py), which is the same limit for ASCII input but
    # not a hard guarantee for multi-byte UTF-8 passwords — a known,
    # accepted edge case, not handled further here.
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(*, user_id: int, org_id: int, role: str) -> str:
    """Encode a JWT carrying user_id (`sub`), org_id, and role as claims."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises `jose.JWTError` on invalid/expired tokens."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
