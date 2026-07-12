"""Scratch/seed script — NOT a migration, NOT a pytest test. Creates two
demo organizations with real users (via the actual signup path, not
hand-rolled DB rows — so passwords are properly hashed the same way a real
signup would produce) and a couple of saved research reports, so a fresh
clone has something to log into and look at immediately, per the
assessment's explicit requirement: "the evaluator should be able to run
your app and see data immediately."

Two orgs, deliberately: this is also the fastest way to demo multi-tenant
isolation live — log in as each org's admin and show neither sees the
other's saved research.

Saved reports use a hand-written StructuredResult rather than a real
run_research_query() call — seeding shouldn't depend on a configured LLM
key or burn API quota (and this project has hit real Gemini free-tier
exhaustion more than once), and a demo report needs to render
deterministically regardless of provider availability.

Idempotent: re-running skips any user whose email is already registered,
rather than failing or duplicating.

Run from backend/:
    poetry run python scripts/seed_demo_data.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tenancy import ScopedSession  # noqa: E402
from app.schemas.auth import SignupRequest  # noqa: E402
from app.schemas.research import StructuredResult  # noqa: E402
from app.services import auth_service, org_service, report_service  # noqa: E402

DEMO_PASSWORD = "demo-password-123"  # 8-72 chars per app/schemas/auth.py; no complexity rules (NIST SP 800-63B)

TESLA_REPORT = StructuredResult.model_validate(
    {
        "company_cards": [
            {
                "ticker": "TSLA",
                "price": 248.50,
                "change_percent": 2.14,
                "key_metrics": {"pe_ratio": 68.3, "market_cap": 790_000_000_000, "eps": 3.64, "volume": 92_400_000},
            }
        ],
        "comparison_table": None,
        "news_items": [
            {
                "title": "Tesla deliveries beat analyst estimates for the quarter",
                "source": "Reuters",
                "url": "https://example.com/tesla-deliveries",
                "sentiment": "positive",
                "published_at": "2026-07-01T00:00:00Z",
            },
            {
                "title": "Tesla faces new scrutiny over Autopilot safety claims",
                "source": "Bloomberg",
                "url": "https://example.com/tesla-autopilot",
                "sentiment": "negative",
                "published_at": "2026-07-05T00:00:00Z",
            },
        ],
        "risk_summary": (
            "Tesla's production ramp at newer factories remains a key execution risk, and "
            "regulatory scrutiny of Autopilot/FSD claims is an ongoing overhang on sentiment. "
            "Delivery numbers this quarter came in ahead of estimates, which partially offsets "
            "those concerns in the near term."
        ),
        "sources": [
            {
                "claim_text": "Production ramp at newer factories is a key execution risk.",
                "source_type": "filing",
                "source_ref": "TSLA 10-K",
            },
            {
                "claim_text": "Tesla deliveries beat analyst estimates for the quarter.",
                "source_type": "news",
                "source_ref": "https://example.com/tesla-deliveries",
            },
        ],
    }
)

NVDA_AMD_REPORT = StructuredResult.model_validate(
    {
        "company_cards": [
            {
                "ticker": "NVDA",
                "price": 178.20,
                "change_percent": 1.05,
                "key_metrics": {"pe_ratio": 71.5, "market_cap": 4_400_000_000_000, "eps": 2.49, "volume": 210_000_000},
            },
            {
                "ticker": "AMD",
                "price": 172.85,
                "change_percent": -0.62,
                "key_metrics": {"pe_ratio": 112.4, "market_cap": 280_000_000_000, "eps": 1.54, "volume": 48_000_000},
            },
        ],
        "comparison_table": [
            {"ticker": "NVDA", "metric": "P/E ratio", "value": "71.5"},
            {"ticker": "AMD", "metric": "P/E ratio", "value": "112.4"},
            {"ticker": "NVDA", "metric": "Market cap", "value": "$4.4T"},
            {"ticker": "AMD", "metric": "Market cap", "value": "$280B"},
        ],
        "news_items": [
            {
                "title": "AMD gains data center market share against NVIDIA in latest quarter",
                "source": "Reuters",
                "url": "https://example.com/amd-datacenter",
                "sentiment": "positive",
                "published_at": "2026-06-28T00:00:00Z",
            }
        ],
        "risk_summary": (
            "NVIDIA maintains a dominant position in AI accelerators with a much larger market "
            "cap and premium valuation; AMD trades at a higher P/E despite a smaller cap, "
            "reflecting growth expectations as it gains share in data center GPUs."
        ),
        "sources": [
            {
                "claim_text": "AMD gains data center market share against NVIDIA.",
                "source_type": "news",
                "source_ref": "https://example.com/amd-datacenter",
            }
        ],
    }
)


def _signup_or_skip(db, *, email: str, org_name: str | None, org_invite_code: str | None):
    try:
        user = auth_service.signup(
            db,
            SignupRequest(
                email=email, password=DEMO_PASSWORD, org_name=org_name, org_invite_code=org_invite_code
            ),
        )
        print(f"  created {email} (org_id={user.org_id}, role={user.role.value})")
        return user
    except auth_service.EmailAlreadyRegisteredError:
        from app.models import User

        user = db.query(User).filter(User.email == email).first()
        print(f"  {email} already exists (org_id={user.org_id}, role={user.role.value}) — skipping")
        return user


def _seed_report_if_missing(db, *, org_id: int, user_id: int, query_text: str, result: StructuredResult):
    from app.models import ResearchReport

    existing = (
        db.query(ResearchReport)
        .filter(ResearchReport.org_id == org_id, ResearchReport.query_text == query_text)
        .first()
    )
    if existing is not None:
        print(f"  report {query_text!r} already exists (id={existing.id}) — skipping")
        return
    scoped = ScopedSession(db, org_id=org_id)
    report = report_service.save_report(
        scoped, created_by_user_id=user_id, query_text=query_text, structured_result=result
    )
    print(f"  saved report {query_text!r} (id={report.id})")


def main() -> None:
    db = SessionLocal()
    try:
        print("Org 1: Acme Capital")
        acme_admin = _signup_or_skip(
            db, email="admin@acmecapital.demo", org_name="Acme Capital", org_invite_code=None
        )
        invite = org_service.create_invite_code(db, acme_admin.org_id)
        _signup_or_skip(db, email="analyst@acmecapital.demo", org_name=None, org_invite_code=invite.code)

        _seed_report_if_missing(
            db,
            org_id=acme_admin.org_id,
            user_id=acme_admin.id,
            query_text="Give me a quick overview of Tesla",
            result=TESLA_REPORT,
        )
        _seed_report_if_missing(
            db,
            org_id=acme_admin.org_id,
            user_id=acme_admin.id,
            query_text="Compare NVIDIA and AMD stock performance",
            result=NVDA_AMD_REPORT,
        )

        print("\nOrg 2: Beta Investments (for cross-tenant isolation demo — should see none of Acme's data)")
        _signup_or_skip(
            db, email="admin@betainvestments.demo", org_name="Beta Investments", org_invite_code=None
        )

        print(f"\nAll demo accounts use password: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
