"""Response schemas for organization creation (TDD Section 5:
`POST /orgs {name} -> {org, invite_code} [admin]`).

Request-side validation (`OrgCreateRequest`) isn't defined yet — out of
scope for this pass, which is schemas only for what's already been asked
for. It'll be needed once the `/orgs` route is implemented.
"""

from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserRole


class OrganizationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str


class InviteCodeResponse(BaseModel):
    model_config = {"from_attributes": True}

    code: str
    expires_at: datetime


class OrgCreateResponse(BaseModel):
    org: OrganizationResponse
    invite_code: InviteCodeResponse


class OrgMemberResponse(BaseModel):
    """One row in the admin-only team roster (GET /orgs/members) — the
    concrete "manages workspace" capability, distinct from generating an
    invite code.
    """

    model_config = {"from_attributes": True}

    id: int
    email: str
    role: UserRole
    created_at: datetime


class OrgMembersResponse(BaseModel):
    members: list[OrgMemberResponse]
