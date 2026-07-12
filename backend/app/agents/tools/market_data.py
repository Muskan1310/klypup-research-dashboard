"""Market data tool (TDD Section 6, Section 7): wraps the Alpha Vantage API.

Async since adding a second tool (news_search.py) makes real parallel
execution meaningful: TDD Section 6 step 3 calls for asyncio.gather across
independent I/O-bound tool calls, which only pays off once there's more
than one tool for the orchestrator to run concurrently. This module still
has zero LLM SDK dependency — TDD Section 7's core point about tool-calling
is that *our* code executes the tool, not the model.

Alpha Vantage's free tier has an easy-to-miss failure mode: a rate-limited
or malformed request still comes back as HTTP 200, with the actual error
expressed only inside the JSON body (a "Note"/"Information"/"Error Message"
key instead of real data). A bare `response.raise_for_status()` would never
catch this. CLAUDE.md hard constraint #7 requires errors to be explicit,
not silent, so we check for those keys explicitly and treat them exactly
like a network timeout or non-200 response: a structured
`{"status": "failed", "reason": ...}`, never a raised exception.
"""

import asyncio

import httpx

from app.core.config import settings

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
REQUEST_TIMEOUT_SECONDS = 10.0
# Alpha Vantage's free tier enforces a hard 1-request/second burst limit —
# empirically confirmed, not just documented: back-to-back GLOBAL_QUOTE +
# OVERVIEW calls with no spacing reliably tripped it. Sleeping briefly
# between the two calls this function always makes is cheaper than losing
# an entire get_stock_data() call (and burning 2 of the 25/day free-tier
# requests) to a rate-limit response.
BURST_LIMIT_COOLDOWN_SECONDS = 1.1


class _AlphaVantageError(Exception):
    """Internal-only: raised by `_fetch_alpha_vantage` so `get_stock_data`
    has one place to catch and convert into the `{"status": "failed"}`
    shape. Never escapes this module.
    """


async def get_stock_data(ticker: str) -> dict:
    """Fetch current price/volume/change (GLOBAL_QUOTE) and fundamentals
    (OVERVIEW) for `ticker` from Alpha Vantage.

    Returns, on success:
        {"status": "ok", "ticker": "IBM", "price": 223.43,
         "change_percent": 1.23, "volume": 3821020, "pe_ratio": 23.45,
         "market_cap": 205000000000, "eps": 9.87}

    `pe_ratio`/`market_cap`/`eps` come back as `None` (not a failure) if
    Alpha Vantage doesn't cover fundamentals for this ticker — losing
    those three fields shouldn't discard the price/volume data we do have.

    Returns, on ANY failure (bad ticker, network error, timeout, rate
    limit, unexpected response shape):
        {"status": "failed", "reason": "<human-readable explanation>"}

    Never raises.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        return {"status": "failed", "reason": "ticker must not be empty"}

    try:
        async with httpx.AsyncClient() as client:
            quote_data = await _fetch_alpha_vantage(client, function="GLOBAL_QUOTE", symbol=symbol)
            await asyncio.sleep(BURST_LIMIT_COOLDOWN_SECONDS)
            overview_data = await _fetch_alpha_vantage(client, function="OVERVIEW", symbol=symbol)
    except _AlphaVantageError as exc:
        return {"status": "failed", "reason": str(exc)}

    global_quote = quote_data.get("Global Quote") or {}
    if not global_quote:
        return {
            "status": "failed",
            "reason": f"Alpha Vantage returned no quote data for '{symbol}' — check the ticker is valid.",
        }

    try:
        return {
            "status": "ok",
            "ticker": symbol,
            "price": float(global_quote["05. price"]),
            "change_percent": float(global_quote["10. change percent"].rstrip("%")),
            "volume": int(global_quote["06. volume"]),
            "pe_ratio": _parse_optional_float(overview_data.get("PERatio")),
            "market_cap": _parse_optional_int(overview_data.get("MarketCapitalization")),
            "eps": _parse_optional_float(overview_data.get("EPS")),
        }
    except (KeyError, ValueError) as exc:
        return {
            "status": "failed",
            "reason": f"Unexpected response shape from Alpha Vantage for '{symbol}': {exc}",
        }


async def _fetch_alpha_vantage(client: httpx.AsyncClient, *, function: str, symbol: str) -> dict:
    params = {"function": function, "symbol": symbol, "apikey": settings.alpha_vantage_api_key}

    try:
        response = await client.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.TimeoutException as exc:
        raise _AlphaVantageError(f"Alpha Vantage request timed out ({function} {symbol})") from exc
    except httpx.HTTPError as exc:
        raise _AlphaVantageError(f"Alpha Vantage request failed ({function} {symbol}): {exc}") from exc

    if response.status_code != 200:
        raise _AlphaVantageError(
            f"Alpha Vantage returned HTTP {response.status_code} ({function} {symbol})"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise _AlphaVantageError(
            f"Alpha Vantage returned a non-JSON response ({function} {symbol}): {exc}"
        ) from exc

    # The disguised-as-200 failure mode described in the module docstring.
    for error_key in ("Note", "Information", "Error Message"):
        if error_key in data:
            raise _AlphaVantageError(data[error_key])

    return data


def _parse_optional_float(raw: str | None) -> float | None:
    if raw is None or raw in ("", "None", "-"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_optional_int(raw: str | None) -> int | None:
    parsed = _parse_optional_float(raw)
    return int(parsed) if parsed is not None else None
