"""Integration tests for app/api/watchlist.py — same pattern and same
cross-tenant proof as tests/test_api_reports.py.
"""

from uuid import uuid4

from app.models import InviteCode, Organization, User, WatchlistItem

PASSWORD = "a-fairly-long-passphrase"


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
            "org_name": f"Watchlist Test Org {uuid4().hex}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup(db_session, user_ids: list[int], org_ids: list[int]) -> None:
    if user_ids:
        db_session.query(WatchlistItem).filter(WatchlistItem.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        db_session.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    for org_id in org_ids:
        db_session.query(InviteCode).filter(InviteCode.org_id == org_id).delete(
            synchronize_session=False
        )
        db_session.query(WatchlistItem).filter(WatchlistItem.org_id == org_id).delete(
            synchronize_session=False
        )
    if org_ids:
        db_session.query(Organization).filter(Organization.id.in_(org_ids)).delete(
            synchronize_session=False
        )
    db_session.commit()


def test_add_list_and_dedupe_watchlist_items(client, db_session):
    user_ids: list[int] = []
    org_ids: list[int] = []
    try:
        founder = _signup_founder(client, "founder")
        user_ids.append(founder["user"]["id"])
        org_ids.append(founder["user"]["org_id"])
        token = founder["access_token"]

        add_resp = client.post("/watchlist", headers=_auth_header(token), json={"ticker": "tsla"})
        assert add_resp.status_code == 201, add_resp.text
        assert add_resp.json()["ticker"] == "TSLA"  # normalized uppercase

        # Adding the same ticker again (any case) is a no-op, not a duplicate row.
        dupe_resp = client.post("/watchlist", headers=_auth_header(token), json={"ticker": "TSLA"})
        assert dupe_resp.status_code == 201, dupe_resp.text
        assert dupe_resp.json()["id"] == add_resp.json()["id"]

        client.post("/watchlist", headers=_auth_header(token), json={"ticker": "NVDA"})

        list_resp = client.get("/watchlist", headers=_auth_header(token))
        assert list_resp.status_code == 200, list_resp.text
        tickers = {item["ticker"] for item in list_resp.json()["items"]}
        assert tickers == {"TSLA", "NVDA"}
    finally:
        _cleanup(db_session, user_ids, org_ids)


def test_cross_tenant_delete_returns_404_not_403(client, db_session):
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

        add_resp = client.post("/watchlist", headers=_auth_header(token_a), json={"ticker": "TSLA"})
        item_id = add_resp.json()["id"]

        # Org B, holding a valid JWT for its own org, gets 404 — not 403 —
        # deleting org A's watchlist item.
        delete_as_b = client.delete(f"/watchlist/{item_id}", headers=_auth_header(token_b))
        assert delete_as_b.status_code == 404

        # Org B never even sees it in its own list.
        list_as_b = client.get("/watchlist", headers=_auth_header(token_b))
        assert list_as_b.json()["items"] == []

        # Org A can still delete its own item fine — proves the 404 above
        # was tenant-scoping, not a broken route.
        delete_as_a = client.delete(f"/watchlist/{item_id}", headers=_auth_header(token_a))
        assert delete_as_a.status_code == 204
    finally:
        _cleanup(db_session, user_ids, org_ids)
