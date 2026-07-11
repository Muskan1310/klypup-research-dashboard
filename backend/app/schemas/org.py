"""Response schemas for organization creation (TDD Section 5:
`POST /orgs {name} -> {org, invite_code} [admin]`).

Request-side validation (`OrgCreateRequest`) isn't defined yet — out of
scope for this pass, which is schemas only for what's already been asked
for. It'll be needed once the `/orgs` route is implemented.
"""

from datetime import datetime

from pydantic import BaseModel


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
