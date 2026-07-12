"""Manual, one-off script — NOT a pytest test. It lives outside tests/ and
isn't named test_*, so pytest never collects it. Its whole point is the
opposite of tests/test_news_search.py: hit the REAL NewsAPI once and print
what actually comes back (articles + sentiment classification), so you can
eyeball real data instead of trusting mocked responses.

Run from backend/:
    poetry run python scripts/manual_check_news_search.py [COMPANY]

Requires a real NEWS_API_KEY in backend/.env — this script does not fall
back to a mock or demo mode (NewsAPI has no public demo key the way Alpha
Vantage does).
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.tools.news_search import search_news  # noqa: E402

if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Tesla"
    print(f"Fetching real news for {company!r} from NewsAPI...\n")
    result = asyncio.run(search_news(company))
    print(json.dumps(result, indent=2))
