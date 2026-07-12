"""Manual, one-off script — NOT a pytest test. It lives outside tests/ and
isn't named test_*, so pytest never collects it. Its whole point is the
opposite of tests/test_market_data.py: hit the REAL Alpha Vantage API once
and print what actually comes back, so you can eyeball real data instead
of trusting mocked responses.

Run from backend/:
    poetry run python scripts/manual_check_market_data.py [TICKER]

If ALPHA_VANTAGE_API_KEY isn't set in your environment/.env, this falls
back to Alpha Vantage's public "demo" key, which only works for the
symbol IBM (Alpha Vantage locks the demo key to that one ticker). It's
still a real HTTP call against the real API — just restricted to IBM.
Set a real key (see .env.example) to check a different ticker.
"""

import asyncio
import json
import os
import sys

# Run directly (`python scripts/manual_check_market_data.py`), so `app` isn't
# on sys.path yet the way it would be under `poetry run pytest` from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if not os.environ.get("ALPHA_VANTAGE_API_KEY"):
    print(
        "No ALPHA_VANTAGE_API_KEY found in the environment — falling back to "
        "Alpha Vantage's public 'demo' key (locked to ticker IBM only).\n"
    )
    os.environ["ALPHA_VANTAGE_API_KEY"] = "demo"

from app.agents.tools.market_data import get_stock_data  # noqa: E402 (must follow the env fallback above)

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "IBM"

    if os.environ["ALPHA_VANTAGE_API_KEY"] == "demo" and ticker.upper() != "IBM":
        print(f"Demo key only supports IBM — ignoring requested ticker {ticker!r}, using IBM.\n")
        ticker = "IBM"

    print(f"Fetching real market data for {ticker!r} from Alpha Vantage...\n")
    result = asyncio.run(get_stock_data(ticker))
    print(json.dumps(result, indent=2))
