"""Request/response schemas for authentication (TDD Section 5, Section 9).

Password length policy: minimum 8 characters, following NIST SP 800-63B
guidance that length is what matters, not forced complexity rules like
"must contain a symbol" (which push users toward predictable substitutions
like "Password1!" rather than actually harder-to-guess passwords). Maximum
is capped at 72 characters — not an arbitrary round number: bcrypt (our
hashing algorithm, CLAUDE.md hard constraint #5) only considers the first
72 bytes of input and silently truncates anything beyond that, so accepting
a longer password would create a false sense of entropy that never
actually gets hashed.

The minimum length is enforced only on `SignupRequest`, not `LoginRequest`.
That's deliberate: minimum length is a policy for *creating* a password,
not a property a *credential check* should assert — a login schema's job
is "does this string match what's stored," and if a strength policy tightens
later, existing users' logins shouldn't start failing Pydantic validation
before they even reach the password comparison. The 72-char max is applied
to both, though, since that's a hard input-size boundary (defends against
oversized payloads generally, TDD Section 13) rather than a strength policy.

`org_name` is conditionally required: mandatory when founding a new org
(no `org_invite_code`), meaningless when joining one via invite code (the
org already has a name). The model validator below enforces that — and
normalizes `org_name` to `None` whenever an invite code is present, so
"ignored if provided" is an actual guarantee at the schema boundary, not
just something the service layer has to remember not to read.
"""

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.user import UserRole

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 72


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    org_invite_code: str | None = Field(default=None, max_length=64)
    org_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _org_name_required_iff_founding_org(self) -> "SignupRequest":
        if self.org_invite_code:
            # Joining an existing org via invite code — any org_name the
            # client sent is irrelevant, so we drop it rather than leave a
            # value around that nothing downstream should ever read.
            self.org_name = None
        elif not self.org_name:
            raise ValueError(
                "org_name is required when org_invite_code is not provided "
                "(founding a new organization needs a name for it)"
            )
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    role: UserRole
    org_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
