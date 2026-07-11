"""Proves ScopedSession's structural tenant isolation actually holds: a
session bound to org A cannot see org B's rows, even when explicitly
queried for by primary key. This is the test to point to as evidence
multi-tenancy works, rather than a claim about it.
"""

from app.core.tenancy import ScopedSession
from app.models import Organization, User, UserRole


def test_scoped_session_cannot_see_other_orgs_rows(db_session):
    org_a = Organization(name="Tenancy Test Org A")
    org_b = Organization(name="Tenancy Test Org B")
    db_session.add_all([org_a, org_b])
    db_session.commit()

    user_a = User(
        org_id=org_a.id, email="a@tenancy-test.local", hashed_password="x", role=UserRole.ANALYST
    )
    user_b = User(
        org_id=org_b.id, email="b@tenancy-test.local", hashed_password="x", role=UserRole.ANALYST
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()

    try:
        # Sanity check: org B's user really exists and is findable via a
        # plain, unscoped query — otherwise "ScopedSession can't see it"
        # would be true for the trivial, useless reason that nothing exists.
        assert db_session.query(User).filter(User.id == user_b.id).first() is not None

        scoped_to_a = ScopedSession(db_session, org_id=org_a.id)

        # A broad, unfiltered-looking query for ALL users, run through a
        # session scoped to org A, must only ever return org A's rows.
        visible_emails = {u.email for u in scoped_to_a.query_scoped(User).all()}
        assert visible_emails == {user_a.email}
        assert user_b.email not in visible_emails

        # Even an explicit attempt to fetch org B's user by primary key
        # through the org-A-scoped session comes back empty — proving the
        # org_id filter is applied underneath, not just on the initial
        # query, before any caller-added filters are considered.
        assert scoped_to_a.query_scoped(User).filter(User.id == user_b.id).first() is None
    finally:
        db_session.query(User).filter(User.id.in_([user_a.id, user_b.id])).delete(
            synchronize_session=False
        )
        db_session.query(Organization).filter(Organization.id.in_([org_a.id, org_b.id])).delete(
            synchronize_session=False
        )
        db_session.commit()
