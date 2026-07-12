"""Unit tests for app/agents/tools/news_search.py.

NewsAPI's HTTP calls are mocked (monkeypatched on httpx.AsyncClient.get) —
never real — so these run offline and don't burn the free tier's
100-requests/day quota. To see the tool hit the REAL API with real data,
run scripts/manual_check_news_search.py (not a pytest test, not collected
here).
"""

import asyncio

import httpx

from app.agents.tools.news_search import search_news


def _fake_get_for(status_code: int, body: dict):
    async def fake_get(self, url, params=None, timeout=None):
        return httpx.Response(status_code, json=body, request=httpx.Request("GET", url))

    return fake_get


def test_search_news_success(monkeypatch):
    body = {
        "status": "ok",
        "totalResults": 2,
        "articles": [
            {
                "title": "Tesla stock surges on record deliveries",
                "description": "Shares rally after a strong quarter.",
                "source": {"id": "reuters", "name": "Reuters"},
                "url": "https://example.com/a1",
                "publishedAt": "2026-07-10T12:00:00Z",
            },
            {
                "title": "Tesla faces lawsuit over recall",
                "description": "Investigation into safety issue continues.",
                "source": {"id": None, "name": "TechCrunch"},
                "url": "https://example.com/a2",
                "publishedAt": "2026-07-09T08:30:00Z",
            },
            {
                "title": "Tesla opens new factory",
                "description": "Company announces expansion plans.",
                "source": {"id": None, "name": "Wire Service"},
                "url": "https://example.com/a3",
                "publishedAt": "2026-07-08T09:00:00Z",
            },
        ],
    }
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(200, body))

    result = asyncio.run(search_news("Tesla"))

    assert result == [
        {
            "title": "Tesla stock surges on record deliveries",
            "source": "Reuters",
            "url": "https://example.com/a1",
            "published_at": "2026-07-10T12:00:00Z",
            "sentiment": "positive",
        },
        {
            "title": "Tesla faces lawsuit over recall",
            "source": "TechCrunch",
            "url": "https://example.com/a2",
            "published_at": "2026-07-09T08:30:00Z",
            "sentiment": "negative",
        },
        {
            "title": "Tesla opens new factory",
            "source": "Wire Service",
            "url": "https://example.com/a3",
            "published_at": "2026-07-08T09:00:00Z",
            "sentiment": "neutral",
        },
    ]


def test_search_news_empty_results(monkeypatch):
    body = {"status": "ok", "totalResults": 0, "articles": []}
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(200, body))

    result = asyncio.run(search_news("SomeObscureCompanyXYZ"))

    assert result == []


def test_search_news_rate_limited(monkeypatch):
    body = {
        "status": "error",
        "code": "rateLimited",
        "message": "You have made too many requests recently.",
    }
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(429, body))

    result = asyncio.run(search_news("Tesla"))

    assert result["status"] == "failed"
    assert "too many requests" in result["reason"].lower()


def test_search_news_invalid_api_key(monkeypatch):
    body = {
        "status": "error",
        "code": "apiKeyInvalid",
        "message": "Your API key is invalid or incorrect.",
    }
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(401, body))

    result = asyncio.run(search_news("Tesla"))

    assert result["status"] == "failed"
    assert "invalid" in result["reason"].lower()


def test_search_news_network_error_does_not_raise(monkeypatch):
    async def fake_get(self, url, params=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(search_news("Tesla"))

    assert result["status"] == "failed"
    assert "connection refused" in result["reason"].lower()


def test_search_news_empty_company_fails_without_a_network_call(monkeypatch):
    async def fake_get(self, *args, **kwargs):
        raise AssertionError("should never call NewsAPI for an empty company name")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(search_news("   "))

    assert result == {"status": "failed", "reason": "company must not be empty"}


def test_search_news_missing_optional_fields_use_fallbacks(monkeypatch):
    # description can be null, and source.name can be missing entirely —
    # neither should crash sentiment classification or the article mapping.
    body = {
        "status": "ok",
        "totalResults": 1,
        "articles": [
            {
                "title": "Tesla update",
                "description": None,
                "source": {},
                "url": "https://example.com/a1",
                "publishedAt": "2026-07-10T12:00:00Z",
            }
        ],
    }
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(200, body))

    result = asyncio.run(search_news("Tesla"))

    assert result[0]["source"] == "Unknown"
    assert result[0]["sentiment"] == "neutral"
