"""Integration tests for the auth + orgs routes (app/api/auth.py,
app/api/orgs.py), exercised through FastAPI's TestClient end-to-end (real
HTTP request parsing, real JWT issuance/validation, real Postgres) — not
calling the service functions directly, since the thing actually being
proven here is that the route wiring (require_role, get_current_user,
status code mapping) behaves correctly, not just the service logic
(already covered by tests/test_auth_service.py).
"""

from uuid import uuid4

from app.models import InviteCode, Organization, User

PASSWORD = "a-fairly-long-passphrase"


def _unique_email(label: str) -> str:
    return f"{label}-{uuid4().hex}@example.com"


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _signup(client, **payload) -> dict:
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup(db_session, user_ids: list[int], org_id: int | None) -> None:
    if user_ids:
        db_session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    if org_id is not None:
        db_session.query(InviteCode).filter(InviteCode.org_id == org_id).delete(
            synchronize_session=False
        )
        db_session.query(Organization).filter(Organization.id == org_id).delete(
            synchronize_session=False
        )
    db_session.commit()


def test_analyst_forbidden_admin_allowed_to_create_invite_code(client, db_session):
    user_ids: list[int] = []
    org_id = None
    try:
        founder = _signup(
            client,
            email=_unique_email("founder"),
            password=PASSWORD,
            org_name=f"RBAC Test Org {uuid4().hex}",
        )
        user_ids.append(founder["user"]["id"])
        org_id = founder["user"]["org_id"]
        admin_token = founder["access_token"]

        # Admin mints a code so we have an analyst to test the 403 with.
        invite_resp = client.post("/orgs/invite-codes", headers=_auth_header(admin_token))
        assert invite_resp.status_code == 201, invite_resp.text
        invite_code = invite_resp.json()["code"]

        analyst = _signup(
            client, email=_unique_email("analyst"), password=PASSWORD, org_invite_code=invite_code
        )
        user_ids.append(analyst["user"]["id"])
        assert analyst["user"]["role"] == "analyst"
        analyst_token = analyst["access_token"]

        # The actual assertions this test exists for.
        analyst_attempt = client.post("/orgs/invite-codes", headers=_auth_header(analyst_token))
        assert analyst_attempt.status_code == 403

        admin_attempt = client.post("/orgs/invite-codes", headers=_auth_header(admin_token))
        assert admin_attempt.status_code == 201
    finally:
        _cleanup(db_session, user_ids, org_id)


def test_full_invite_flow_join_then_reuse_fails(client, db_session):
    user_ids: list[int] = []
    org_id = None
    try:
        founder = _signup(
            client,
            email=_unique_email("founder2"),
            password=PASSWORD,
            org_name=f"Integration Test Org {uuid4().hex}",
        )
        user_ids.append(founder["user"]["id"])
        org_id = founder["user"]["org_id"]
        admin_token = founder["access_token"]

        invite_resp = client.post("/orgs/invite-codes", headers=_auth_header(admin_token))
        assert invite_resp.status_code == 201, invite_resp.text
        invite_code = invite_resp.json()["code"]

        second_user = _signup(
            client, email=_unique_email("second"), password=PASSWORD, org_invite_code=invite_code
        )
        user_ids.append(second_user["user"]["id"])
        assert second_user["user"]["org_id"] == org_id
        assert second_user["user"]["role"] == "analyst"

        # Reusing the same code for a third signup must fail — the invite
        # was already redeemed by the second user above.
        third_response = client.post(
            "/auth/signup",
            json={
                "email": _unique_email("third"),
                "password": PASSWORD,
                "org_invite_code": invite_code,
            },
        )
        assert third_response.status_code == 400
    finally:
        _cleanup(db_session, user_ids, org_id)
