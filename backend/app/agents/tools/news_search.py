"""News search tool (TDD Section 6, Section 7): wraps NewsAPI's
`/v2/everything` endpoint.

Async to match `get_stock_data` (app/agents/tools/market_data.py) — both
tools are real I/O-bound async functions so the orchestrator can run them
concurrently via `asyncio.gather` (TDD Section 6 step 3), which only pays
off once there's more than one tool to run in parallel.

Sentiment is classified via a small keyword word-list, not another LLM
call — a deliberate cost/complexity tradeoff. Running every returned
article through Claude/Gemini for sentiment would multiply this tool's
latency and token cost by however many articles come back, for a signal
("mostly positive/negative/neutral coverage") a cheap heuristic already
captures well enough for a research-summary use case. If sentiment
*accuracy* became a real product requirement rather than a rough signal,
this is the point to revisit.

NewsAPI's error handling is simpler than Alpha Vantage's: real non-200 HTTP
status codes for failures (400/401/429/500), not a disguised-as-200
failure mode — verified against NewsAPI's own docs, not assumed, since
Alpha Vantage's sneaky pattern is exactly the kind of thing worth
double-checking rather than guessing is the same everywhere. Their free
"Developer" plan's only documented limit is 100 requests/day (no
per-second burst limit like Alpha Vantage's, which is what forced the
cooldown in market_data.py), and this function makes exactly one HTTP call
per invocation — so there's no intra-call spacing to add here.
"""

import re
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings

NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"
REQUEST_TIMEOUT_SECONDS = 10.0
LOOKBACK_DAYS = 30
# Keep the tool_result payload sent back to the LLM small and cheap —
# NewsAPI's own default page size is 100, far more than a research
# synthesis prompt needs to ground an answer.
MAX_ARTICLES = 10

# Small, hand-picked word lists for keyword-based sentiment — see module
# docstring for why this isn't an LLM call.
_POSITIVE_WORDS = {
    "surge", "surges", "soar", "soars", "rally", "rallies", "gain", "gains",
    "growth", "profit", "profits", "beat", "beats", "record", "boost",
    "upgrade", "outperform", "strong", "rise", "rises", "jump", "jumps",
    "win", "wins", "success",
}
_NEGATIVE_WORDS = {
    "plunge", "plunges", "plummet", "plummets", "crash", "crashes", "loss",
    "losses", "decline", "declines", "lawsuit", "investigation", "recall",
    "miss", "misses", "drop", "drops", "fall", "falls", "downgrade",
    "underperform", "weak", "cut", "cuts", "layoff", "layoffs", "fraud",
    "scandal",
}
_WORD_PATTERN = re.compile(r"[a-z']+")


class _NewsAPIError(Exception):
    """Internal-only: raised by `_fetch_newsapi` so `search_news` has one
    place to catch and convert into the `{"status": "failed"}` shape.
    Never escapes this module.
    """


async def search_news(company: str) -> list[dict] | dict:
    """Fetch recent news articles mentioning `company` from NewsAPI,
    filtered to the last 30 days, sorted by relevancy.

    Returns, on success, a list of article dicts (up to `MAX_ARTICLES`):
        [{"title": ..., "source": "Reuters", "url": ...,
          "published_at": "2026-07-10T12:00:00Z",
          "sentiment": "positive" | "negative" | "neutral"}, ...]

    An empty result set (no matching articles) is still success — an empty
    list, not a failure. Note the return type is a list on success but a
    dict on failure — unlike `get_stock_data`, which is always a dict —
    because the task here is inherently "return N things," not "return one
    thing or explain why not."

    Returns, on ANY failure (bad/missing key, rate limit, network error,
    timeout, unexpected response shape):
        {"status": "failed", "reason": "<human-readable explanation>"}

    Never raises.
    """
    query = company.strip()
    if not query:
        return {"status": "failed", "reason": "company must not be empty"}

    from_date = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    params = {
        "q": query,
        "from": from_date,
        "sortBy": "relevancy",
        "language": "en",  # keyword-based sentiment below assumes English
        "pageSize": MAX_ARTICLES,
        "apiKey": settings.news_api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            data = await _fetch_newsapi(client, params)
    except _NewsAPIError as exc:
        return {"status": "failed", "reason": str(exc)}

    articles = data.get("articles") or []

    try:
        return [_to_article_dict(article) for article in articles]
    except (KeyError, TypeError) as exc:
        return {
            "status": "failed",
            "reason": f"Unexpected response shape from NewsAPI for '{query}': {exc}",
        }


async def _fetch_newsapi(client: httpx.AsyncClient, params: dict) -> dict:
    try:
        response = await client.get(NEWSAPI_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.TimeoutException as exc:
        raise _NewsAPIError(f"NewsAPI request timed out (query '{params['q']}')") from exc
    except httpx.HTTPError as exc:
        raise _NewsAPIError(f"NewsAPI request failed (query '{params['q']}'): {exc}") from exc

    if response.status_code != 200:
        # NewsAPI uses real HTTP status codes for errors and puts a
        # human-readable message in the JSON body — surface that instead
        # of just the bare status code.
        try:
            reason = response.json().get("message", f"HTTP {response.status_code}")
        except ValueError:
            reason = f"HTTP {response.status_code}"
        raise _NewsAPIError(f"NewsAPI returned an error (query '{params['q']}'): {reason}")

    try:
        return response.json()
    except ValueError as exc:
        raise _NewsAPIError(
            f"NewsAPI returned a non-JSON response (query '{params['q']}'): {exc}"
        ) from exc


def _to_article_dict(article: dict) -> dict:
    title = article.get("title") or ""
    description = article.get("description") or ""
    return {
        "title": title,
        "source": (article.get("source") or {}).get("name") or "Unknown",
        "url": article["url"],
        "published_at": article["publishedAt"],
        "sentiment": _classify_sentiment(f"{title} {description}"),
    }


def _classify_sentiment(text: str) -> str:
    words = set(_WORD_PATTERN.findall(text.lower()))
    positive_hits = len(words & _POSITIVE_WORDS)
    negative_hits = len(words & _NEGATIVE_WORDS)
    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"
