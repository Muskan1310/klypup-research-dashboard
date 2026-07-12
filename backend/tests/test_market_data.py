"""Unit tests for app/agents/tools/market_data.py.

Alpha Vantage's HTTP calls are mocked (monkeypatched on httpx.AsyncClient.get)
— never real — so these run offline and don't burn the free tier's
25-requests/day quota. To see the tool hit the REAL API with real data, run
scripts/manual_check_market_data.py (not a pytest test, not collected here).
"""

import asyncio

import httpx
import pytest

from app.agents.tools.market_data import get_stock_data


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    # get_stock_data() sleeps between its two real Alpha Vantage calls to
    # respect the free tier's burst limit — irrelevant with a mocked
    # httpx.AsyncClient.get, and would otherwise add ~1.1s to every test
    # that exercises both calls.
    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("app.agents.tools.market_data.asyncio.sleep", fake_sleep)


GLOBAL_QUOTE_RESPONSE = {
    "Global Quote": {
        "01. symbol": "IBM",
        "05. price": "223.4300",
        "06. volume": "3821020",
        "10. change percent": "1.2345%",
    }
}

OVERVIEW_RESPONSE = {
    "Symbol": "IBM",
    "PERatio": "23.45",
    "MarketCapitalization": "205000000000",
    "EPS": "9.87",
}


def _fake_get_for(quote_body: dict, overview_body: dict):
    async def fake_get(self, url, params=None, timeout=None):
        body = quote_body if params["function"] == "GLOBAL_QUOTE" else overview_body
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))

    return fake_get


def test_get_stock_data_success(monkeypatch):
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(GLOBAL_QUOTE_RESPONSE, OVERVIEW_RESPONSE))

    result = asyncio.run(get_stock_data("ibm"))  # lowercase in, uppercase out

    assert result == {
        "status": "ok",
        "ticker": "IBM",
        "price": 223.43,
        "change_percent": 1.2345,
        "volume": 3821020,
        "pe_ratio": 23.45,
        "market_cap": 205000000000,
        "eps": 9.87,
    }


def test_get_stock_data_handles_missing_fundamentals_without_failing(monkeypatch):
    # OVERVIEW sometimes reports "None" (the literal string) for fields it
    # doesn't have — this must not fail the whole call, since price/volume
    # data from GLOBAL_QUOTE is still valid and useful on its own.
    sparse_overview = {"Symbol": "IBM", "PERatio": "None", "MarketCapitalization": "None", "EPS": "None"}
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(GLOBAL_QUOTE_RESPONSE, sparse_overview))

    result = asyncio.run(get_stock_data("IBM"))

    assert result["status"] == "ok"
    assert result["pe_ratio"] is None
    assert result["market_cap"] is None
    assert result["eps"] is None
    assert result["price"] == 223.43  # unaffected


def test_get_stock_data_rate_limit_disguised_as_http_200(monkeypatch):
    # This is the failure mode this module's docstring is about: Alpha
    # Vantage returns HTTP 200 with the actual error only inside the JSON
    # body. response.raise_for_status() would never catch this.
    rate_limit_body = {
        "Information": (
            "Thank you for using Alpha Vantage! Our standard API rate limit is "
            "25 requests per day. Please subscribe to any of the premium plans "
            "to instantly remove all daily rate limits."
        )
    }
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(rate_limit_body, rate_limit_body))

    result = asyncio.run(get_stock_data("IBM"))

    assert result["status"] == "failed"
    assert "rate limit" in result["reason"].lower()


def test_get_stock_data_invalid_ticker_error_message(monkeypatch):
    error_body = {"Error Message": "Invalid API call. Please retry or visit the documentation."}
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get_for(error_body, error_body))

    result = asyncio.run(get_stock_data("NOTAREALTICKER"))

    assert result == {
        "status": "failed",
        "reason": "Invalid API call. Please retry or visit the documentation.",
    }


def test_get_stock_data_network_error_does_not_raise(monkeypatch):
    async def fake_get(self, url, params=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(get_stock_data("IBM"))

    assert result["status"] == "failed"
    assert "connection refused" in result["reason"].lower()


def test_get_stock_data_empty_ticker_fails_without_a_network_call(monkeypatch):
    async def fake_get(self, *args, **kwargs):
        raise AssertionError("should never call Alpha Vantage for an empty ticker")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = asyncio.run(get_stock_data("   "))

    assert result == {"status": "failed", "reason": "ticker must not be empty"}
