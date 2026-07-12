"""Integration tests for app/api/reports.py, exercised through FastAPI's
TestClient end-to-end (real HTTP, real JWT, real Postgres) — same pattern
as tests/test_api_orgs.py.

The one test that matters most here (per CLAUDE.md hard constraint #3):
a user from Org A must not be able to GET or DELETE a report belonging to
Org B, and the failure must be 404, not 403 — a 403 would confirm the
report exists in someone else's org, which is itself a tenant-isolation
leak.
"""

from uuid import uuid4

from app.models import InviteCode, Organization, ResearchReport, User

PASSWORD = "a-fairly-long-passphrase"

STRUCTURED_RESULT = {
    "company_cards": [
        {"ticker": "TSLA", "price": 223.43, "change_percent": 1.23, "key_metrics": None}
    ],
    "comparison_table": None,
    "news_items": [],
    "risk_summary": "Tesla faces production risk.",
    "sources": [
        {
            "claim_text": "Tesla faces production risk.",
            "source_type": "filing",
            "source_ref": "TSLA 10-K",
        }
    ],
}


def _unique_email(label: str) -> str:
    return f"{label}-{uuid4().hex}@example.com"


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _signup_founder(client, label: str) -> dict:
    response = client.post(
        "/auth/signup",
        json={
            "email": _unique_email(label),
            "password": PASSWORD,
            "org_name": f"Reports Test Org {uuid4().hex}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup(db_session, user_ids: list[int], org_ids: list[int]) -> None:
    if user_ids:
        db_session.query(ResearchReport).filter(
            ResearchReport.created_by_user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        db_session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    for org_id in org_ids:
        db_session.query(InviteCode).filter(InviteCode.org_id == org_id).delete(
            synchronize_session=False
        )
        db_session.query(ResearchReport).filter(ResearchReport.org_id == org_id).delete(
            synchronize_session=False
        )
    if org_ids:
        db_session.query(Organization).filter(Organization.id.in_(org_ids)).delete(
            synchronize_session=False
        )
    db_session.commit()


def test_save_list_and_get_report_roundtrip(client, db_session):
    user_ids: list[int] = []
    org_ids: list[int] = []
    try:
        founder = _signup_founder(client, "founder")
        user_ids.append(founder["user"]["id"])
        org_ids.append(founder["user"]["org_id"])
        token = founder["access_token"]

        save_resp = client.post(
            "/reports",
            headers=_auth_header(token),
            json={"query_text": "Give me a quick overview of Tesla", "structured_result": STRUCTURED_RESULT},
        )
        assert save_resp.status_code == 201, save_resp.text
        saved = save_resp.json()
        assert saved["query_text"] == "Give me a quick overview of Tesla"
        assert saved["structured_result"]["company_cards"][0]["ticker"] == "TSLA"
        report_id = saved["id"]

        # The report_sources row was actually written, not just the JSONB.
        source_count = (
            db_session.query(ResearchReport)
            .filter(ResearchReport.id == report_id)
            .first()
            .sources
        )
        assert len(source_count) == 1
        assert source_count[0].source_type.value == "filing"

        list_resp = client.get("/reports", headers=_auth_header(token))
        assert list_resp.status_code == 200, list_resp.text
        body = list_resp.json()
        assert body["total"] == 1
        assert body["reports"][0]["id"] == report_id
        assert "structured_result" not in body["reports"][0]

        detail_resp = client.get(f"/reports/{report_id}", headers=_auth_header(token))
        assert detail_resp.status_code == 200, detail_resp.text
        assert detail_resp.json()["structured_result"]["risk_summary"] == "Tesla faces production risk."
    finally:
        _cleanup(db_session, user_ids, org_ids)


def test_cross_tenant_get_and_delete_return_404_not_403(client, db_session):
    user_ids: list[int] = []
    org_ids: list[int] = []
    try:
        org_a = _signup_founder(client, "org-a-founder")
        user_ids.append(org_a["user"]["id"])
        org_ids.append(org_a["user"]["org_id"])
        token_a = org_a["access_token"]

        org_b = _signup_founder(client, "org-b-founder")
        user_ids.append(org_b["user"]["id"])
        org_ids.append(org_b["user"]["org_id"])
        token_b = org_b["access_token"]

        save_resp = client.post(
            "/reports",
            headers=_auth_header(token_a),
            json={"query_text": "Org A's private research", "structured_result": STRUCTURED_RESULT},
        )
        assert save_resp.status_code == 201, save_resp.text
        report_id = save_resp.json()["id"]

        # The actual assertions this test exists for: org B, holding a
        # perfectly valid JWT for its own org, must get 404 — not 403 —
        # both reading and deleting org A's report. 403 would itself leak
        # that a report with this id exists somewhere.
        get_as_b = client.get(f"/reports/{report_id}", headers=_auth_header(token_b))
        assert get_as_b.status_code == 404

        delete_as_b = client.delete(f"/reports/{report_id}", headers=_auth_header(token_b))
        assert delete_as_b.status_code == 404

        # Proof the 404 wasn't because the report doesn't exist at all —
        # org A can still see it fine after org B's failed delete attempt.
        get_as_a = client.get(f"/reports/{report_id}", headers=_auth_header(token_a))
        assert get_as_a.status_code == 200

        # And org A can delete its own report — the 404s above were
        # tenant-scoping, not a broken delete route.
        delete_as_a = client.delete(f"/reports/{report_id}", headers=_auth_header(token_a))
        assert delete_as_a.status_code == 204
    finally:
        _cleanup(db_session, user_ids, org_ids)


def test_get_and_delete_nonexistent_report_returns_404(client, db_session):
    user_ids: list[int] = []
    org_ids: list[int] = []
    try:
        founder = _signup_founder(client, "founder-404")
        user_ids.append(founder["user"]["id"])
        org_ids.append(founder["user"]["org_id"])
        token = founder["access_token"]

        assert client.get("/reports/999999999", headers=_auth_header(token)).status_code == 404
        assert client.delete("/reports/999999999", headers=_auth_header(token)).status_code == 404
    finally:
        _cleanup(db_session, user_ids, org_ids)
