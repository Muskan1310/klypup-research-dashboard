"""Unit tests for app/agents/orchestrator.py (litellm-orchestrator branch).

litellm.acompletion() is mocked (monkeypatched) — never a real call — so
these run offline and cost nothing. To see the orchestrator run against a
REAL LLM provider, run scripts/manual_check_orchestrator.py (not a pytest
test, not collected here).

Fixtures are built from litellm's own response types (ModelResponse,
Choices, Message, ChatCompletionMessageToolCall, Function), the same way
tests/test_market_data.py uses real httpx.Response objects — this tests
against the actual shape litellm returns, not a hand-guessed approximation.
"""

import asyncio
import json
from datetime import datetime

import pytest
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Function,
    Message,
    ModelResponse,
)

from app.agents import orchestrator
from app.agents.orchestrator import run_research_query

# Default valid StructuredResult payload — every field present with its
# empty/default value, so individual tests only need to override the
# field(s) they actually care about (see _structured_response).
_DEFAULT_STRUCTURED_PAYLOAD = {
    "company_cards": [],
    "comparison_table": None,
    "news_items": [],
    "risk_summary": "",
    "sources": [],
}


def _text_response(text: str) -> ModelResponse:
    message = Message(content=text, role="assistant")
    return ModelResponse(choices=[Choices(finish_reason="stop", index=0, message=message)])


def _structured_response(**overrides) -> ModelResponse:
    """A synthesis-call response whose content is JSON matching
    StructuredResult (app/schemas/research.py) — what the real synthesis
    call now returns instead of free text, since it's called with
    response_format=StructuredResult.
    """
    payload = {**_DEFAULT_STRUCTURED_PAYLOAD, **overrides}
    message = Message(content=json.dumps(payload), role="assistant")
    return ModelResponse(choices=[Choices(finish_reason="stop", index=0, message=message)])


def _tool_call_response(*, name: str, args: dict, call_id: str = "call_1") -> ModelResponse:
    tool_call = ChatCompletionMessageToolCall(
        id=call_id,
        type="function",
        function=Function(name=name, arguments=json.dumps(args)),
    )
    message = Message(content=None, role="assistant", tool_calls=[tool_call])
    return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=message)])


def _multi_tool_call_response(calls: list[tuple[str, dict]]) -> ModelResponse:
    tool_calls = [
        ChatCompletionMessageToolCall(
            id=f"call_{i}",
            type="function",
            function=Function(name=name, arguments=json.dumps(args)),
        )
        for i, (name, args) in enumerate(calls)
    ]
    message = Message(content=None, role="assistant", tool_calls=tool_calls)
    return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=message)])


@pytest.fixture(autouse=True)
def _require_configured_key(monkeypatch):
    # run_research_query() checks for a real key before doing anything —
    # give it one so tests exercise the actual code path, not the guard.
    monkeypatch.setattr(orchestrator.settings, "llm_provider", "anthropic")
    monkeypatch.setattr(orchestrator.settings, "anthropic_api_key", "sk-ant-test-key")


@pytest.fixture(autouse=True)
def _clear_research_cache():
    # _research_cache is a module-level dict shared across every call to
    # run_research_query() in this process — several tests below reuse the
    # same query text (e.g. "What's Tesla's current stock price?"), and
    # without clearing between tests a later test would get a cache hit
    # from an earlier one instead of exercising fake_acompletion at all.
    orchestrator._research_cache.clear()
    yield
    orchestrator._research_cache.clear()


def test_run_research_query_calls_tool_and_synthesizes(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _tool_call_response(name="get_stock_data", args={"ticker": "TSLA"})
        return _structured_response(
            company_cards=[{"ticker": "TSLA", "price": 223.43, "change_percent": 1.23, "key_metrics": None}],
            risk_summary="Tesla is trading up slightly today.",
        )

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 223.43, "change_percent": 1.23}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    result = asyncio.run(run_research_query("What's Tesla's current stock price?"))

    assert result["status"] == "ok"
    structured = result["structured_result"]
    assert structured["risk_summary"] == "Tesla is trading up slightly today."
    assert structured["company_cards"] == [
        {"ticker": "TSLA", "price": 223.43, "change_percent": 1.23, "key_metrics": None}
    ]
    assert len(result["tools_called"]) == 1
    call = result["tools_called"][0]
    assert call["name"] == "get_stock_data"
    assert call["input"] == {"ticker": "TSLA"}
    assert call["result"] == {"status": "ok", "ticker": "TSLA", "price": 223.43, "change_percent": 1.23}
    assert datetime.fromisoformat(call["started_at"]) <= datetime.fromisoformat(call["finished_at"])
    assert result["tools_skipped"] == ["search_documents", "search_news"]
    assert len(calls) == 2  # two-pass: planning + synthesis

    # The synthesis call must not offer tools — a third round of tool calls
    # isn't supported by the two-pass design (see orchestrator.py docstring).
    assert "tools" not in calls[1]
    assert calls[1]["response_format"] is orchestrator.StructuredResult


def test_run_research_query_skips_all_tools_for_unrelated_question(monkeypatch):
    async def fake_acompletion(**kwargs):
        return _text_response("The capital of France is Paris.")

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)

    result = asyncio.run(run_research_query("What's the capital of France?"))

    assert result["status"] == "ok"
    assert result["answer"] == "The capital of France is Paris."
    assert result["tools_called"] == []
    assert result["tools_skipped"] == ["get_stock_data", "search_documents", "search_news"]


def test_run_research_query_handles_multiple_calls_to_the_same_tool(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _multi_tool_call_response(
                [("get_stock_data", {"ticker": "NVDA"}), ("get_stock_data", {"ticker": "AMD"})]
            )
        return _structured_response(risk_summary="NVIDIA is up 2%; AMD is down 1% today.")

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 100.0, "change_percent": 0.0}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    result = asyncio.run(run_research_query("Compare NVIDIA and AMD stock performance"))

    assert result["status"] == "ok"
    assert len(result["tools_called"]) == 2
    assert {c["name"] for c in result["tools_called"]} == {"get_stock_data"}
    assert {c["input"]["ticker"] for c in result["tools_called"]} == {"NVDA", "AMD"}
    assert result["tools_skipped"] == ["search_documents", "search_news"]

    # Both tool_result messages were sent back in the second call, per the
    # tool_call_id each individual tool_use produced.
    second_call_messages = calls[1]["messages"]
    tool_messages = [m for m in second_call_messages if m["role"] == "tool"]
    assert {m["tool_call_id"] for m in tool_messages} == {"call_0", "call_1"}


def test_run_research_query_runs_mixed_tool_types_concurrently(monkeypatch):
    # This is the case the litellm-orchestrator branch's asyncio.gather is
    # actually being asked to prove: a MIX of tool types in one turn, not
    # just repeated calls to the same tool.
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _multi_tool_call_response(
                [
                    ("get_stock_data", {"ticker": "NVDA"}),
                    ("search_news", {"company": "NVIDIA"}),
                ]
            )
        return _structured_response(risk_summary="NVIDIA's stock is up and recent coverage is positive.")

    async def fake_get_stock_data(ticker):
        await asyncio.sleep(0.05)
        return {"status": "ok", "ticker": ticker, "price": 100.0, "change_percent": 1.0}

    async def fake_search_news(company):
        await asyncio.sleep(0.05)
        return [
            {
                "title": "Great quarter",
                "source": "Reuters",
                "url": "https://example.com/a1",
                "published_at": "2026-07-01T00:00:00Z",
                "sentiment": "positive",
            }
        ]

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)
    monkeypatch.setattr(orchestrator, "search_news", fake_search_news)

    result = asyncio.run(
        run_research_query("What's the latest news on NVIDIA and how's the stock doing?")
    )

    assert result["status"] == "ok"
    assert {c["name"] for c in result["tools_called"]} == {"get_stock_data", "search_news"}
    assert result["tools_skipped"] == ["search_documents"]

    stock_call = next(c for c in result["tools_called"] if c["name"] == "get_stock_data")
    news_call = next(c for c in result["tools_called"] if c["name"] == "search_news")
    assert stock_call["input"] == {"ticker": "NVDA"}
    assert news_call["input"] == {"company": "NVIDIA"}
    assert stock_call["result"]["status"] == "ok"
    assert news_call["result"][0]["sentiment"] == "positive"

    # Prove concurrency, not just correctness: each tool call sleeps 0.05s.
    # If asyncio.gather ran them sequentially, one call's started_at would
    # be at or after the other's finished_at — no overlap. Running them
    # concurrently means their [started_at, finished_at] windows overlap.
    stock_start = datetime.fromisoformat(stock_call["started_at"])
    stock_end = datetime.fromisoformat(stock_call["finished_at"])
    news_start = datetime.fromisoformat(news_call["started_at"])
    news_end = datetime.fromisoformat(news_call["finished_at"])
    assert stock_start < news_end and news_start < stock_end


def test_run_research_query_dispatches_search_documents_via_thread(monkeypatch):
    # search_documents is a plain sync function (rag/retriever.py) — the
    # orchestrator dispatches it through asyncio.to_thread, unlike the two
    # real-async tools. Mock it as sync too, matching what asyncio.to_thread
    # actually expects to call.
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _tool_call_response(
                name="search_documents", args={"query": "main risk factors", "ticker": "AMD"}
            )
        return _structured_response(
            risk_summary="AMD's filing lists foundry reliance and customer concentration.",
            sources=[
                {
                    "claim_text": "AMD relies on third-party foundries.",
                    "source_type": "filing",
                    "source_ref": "AMD 10-K",
                }
            ],
        )

    def fake_search_documents(query, ticker=None):
        assert query == "main risk factors"
        assert ticker == "AMD"
        return {
            "status": "ok",
            "results": [{"score": 0.32, "text": "risk factors excerpt", "ticker": "AMD"}],
        }

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "search_documents", fake_search_documents)

    result = asyncio.run(run_research_query("What are AMD's main risk factors?"))

    assert result["status"] == "ok"
    assert result["structured_result"]["sources"] == [
        {
            "claim_text": "AMD relies on third-party foundries.",
            "source_type": "filing",
            "source_ref": "AMD 10-K",
        }
    ]
    assert result["tools_called"] == [
        {
            "name": "search_documents",
            "input": {"query": "main risk factors", "ticker": "AMD"},
            "result": {
                "status": "ok",
                "results": [{"score": 0.32, "text": "risk factors excerpt", "ticker": "AMD"}],
            },
            "started_at": result["tools_called"][0]["started_at"],
            "finished_at": result["tools_called"][0]["finished_at"],
        }
    ]
    assert result["tools_skipped"] == ["get_stock_data", "search_news"]


def test_run_research_query_runs_all_three_tool_types_concurrently(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _multi_tool_call_response(
                [
                    ("get_stock_data", {"ticker": "TSLA"}),
                    ("search_news", {"company": "Tesla"}),
                    ("search_documents", {"query": "production risk"}),
                ]
            )
        return _structured_response(risk_summary="Combined answer using all three tools.")

    async def fake_get_stock_data(ticker):
        await asyncio.sleep(0.05)
        return {"status": "ok", "ticker": ticker, "price": 407.76, "change_percent": 0.3}

    async def fake_search_news(company):
        await asyncio.sleep(0.05)
        return []

    def fake_search_documents(query, ticker=None):
        import time

        time.sleep(0.05)  # asyncio.to_thread runs this in a real thread
        return {"status": "ok", "results": [{"score": 0.4, "text": "excerpt", "ticker": "TSLA"}]}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)
    monkeypatch.setattr(orchestrator, "search_news", fake_search_news)
    monkeypatch.setattr(orchestrator, "search_documents", fake_search_documents)

    result = asyncio.run(run_research_query("Tesla: price, news, and production risk"))

    assert result["status"] == "ok"
    assert {c["name"] for c in result["tools_called"]} == {
        "get_stock_data",
        "search_news",
        "search_documents",
    }
    assert result["tools_skipped"] == []

    # All three calls' [started_at, finished_at] windows should mutually
    # overlap if they truly ran concurrently (two via asyncio.gather + real
    # async I/O, one via asyncio.to_thread).
    windows = {
        c["name"]: (datetime.fromisoformat(c["started_at"]), datetime.fromisoformat(c["finished_at"]))
        for c in result["tools_called"]
    }
    names = list(windows)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            start_i, end_i = windows[names[i]]
            start_j, end_j = windows[names[j]]
            assert start_i < end_j and start_j < end_i, f"{names[i]} and {names[j]} did not overlap"


def test_run_research_query_passes_failed_tool_result_without_crashing(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _tool_call_response(name="get_stock_data", args={"ticker": "NOTAREALTICKER"})
        return _structured_response(risk_summary="I wasn't able to retrieve data for that ticker.")

    async def fake_get_stock_data(ticker):
        return {"status": "failed", "reason": "Alpha Vantage returned no quote data"}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    result = asyncio.run(run_research_query("What's the price of NOTAREALTICKER?"))

    assert result["status"] == "ok"
    assert result["structured_result"]["risk_summary"] == "I wasn't able to retrieve data for that ticker."
    assert result["tools_called"][0]["result"]["status"] == "failed"

    # No is_error field in the OpenAI-shaped tool message (unlike Anthropic's
    # tool_result blocks) — the failure is signaled purely via the JSON
    # content, which is the documented tradeoff of this branch.
    tool_message = [m for m in calls[1]["messages"] if m["role"] == "tool"][0]
    assert "is_error" not in tool_message
    assert json.loads(tool_message["content"])["status"] == "failed"


def test_run_research_query_one_failed_tool_does_not_block_the_other(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _multi_tool_call_response(
                [
                    ("get_stock_data", {"ticker": "TSLA"}),
                    ("search_news", {"company": "Tesla"}),
                ]
            )
        return _structured_response(risk_summary="Stock data is available; news search failed.")

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 407.76, "change_percent": 0.3}

    async def fake_search_news(company):
        return {"status": "failed", "reason": "NewsAPI rate limited"}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)
    monkeypatch.setattr(orchestrator, "search_news", fake_search_news)

    result = asyncio.run(run_research_query("Latest news and stock price for Tesla"))

    assert result["status"] == "ok"
    stock_call = next(c for c in result["tools_called"] if c["name"] == "get_stock_data")
    news_call = next(c for c in result["tools_called"] if c["name"] == "search_news")
    assert stock_call["result"]["status"] == "ok"
    assert news_call["result"]["status"] == "failed"
    assert result["tools_skipped"] == ["search_documents"]


def test_run_research_query_handles_malformed_tool_arguments(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            tool_call = ChatCompletionMessageToolCall(
                id="call_1",
                type="function",
                function=Function(name="get_stock_data", arguments="{not valid json"),
            )
            message = Message(content=None, role="assistant", tool_calls=[tool_call])
            return ModelResponse(choices=[Choices(finish_reason="tool_calls", index=0, message=message)])
        return _structured_response(risk_summary="Something went wrong reading that request.")

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)

    result = asyncio.run(run_research_query("What's Tesla's stock price?"))

    assert result["tools_called"][0]["result"]["status"] == "failed"
    assert "malformed" in result["tools_called"][0]["result"]["reason"].lower()


def test_run_research_query_retries_once_on_invalid_synthesis_json_then_succeeds(monkeypatch):
    # TDD Section 11 / CLAUDE.md constraint #7: malformed synthesis output
    # gets one bounded retry, with the validation error fed back to the
    # model, before giving up — this proves the retry actually recovers
    # when the second attempt is valid.
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _tool_call_response(name="get_stock_data", args={"ticker": "TSLA"})
        if len(calls) == 2:
            # Missing required fields / wrong shape entirely.
            return _text_response("not json at all")
        return _structured_response(risk_summary="Recovered on retry.")

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 223.43, "change_percent": 1.23}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    result = asyncio.run(run_research_query("What's Tesla's current stock price?"))

    assert result["status"] == "ok"
    assert result["structured_result"]["risk_summary"] == "Recovered on retry."
    assert len(calls) == 3  # planning + failed synthesis attempt + retry

    # The retry must tell the model what was wrong, in-context.
    retry_messages = calls[2]["messages"]
    assert retry_messages[-2] == {"role": "assistant", "content": "not json at all"}
    assert "did not match the required" in retry_messages[-1]["content"]


def test_run_research_query_returns_malformed_output_after_exhausting_retries(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _tool_call_response(name="get_stock_data", args={"ticker": "TSLA"})
        return _text_response("still not json")

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 223.43, "change_percent": 1.23}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    result = asyncio.run(run_research_query("What's Tesla's current stock price?"))

    assert result["status"] == "malformed_output"
    assert "reason" in result
    assert "2 attempt" in result["reason"]
    assert result["tools_called"][0]["name"] == "get_stock_data"
    assert result["tools_skipped"] == ["search_documents", "search_news"]
    assert len(calls) == 3  # planning + two bounded synthesis attempts, then give up


def test_run_research_query_caches_identical_normalized_queries(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return _tool_call_response(name="get_stock_data", args={"ticker": "TSLA"})
        return _structured_response(risk_summary="Cached-eligible result.")

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 223.43, "change_percent": 1.23}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    first = asyncio.run(run_research_query("What's Tesla's current stock price?"))
    assert first["status"] == "ok"
    assert len(calls) == 2

    # Same question, different case/whitespace — must normalize to the
    # same cache key and short-circuit before any new litellm calls.
    second = asyncio.run(run_research_query("  WHAT'S tesla's   current STOCK price?  "))
    assert second == first
    assert len(calls) == 2


def test_run_research_query_cache_expires_after_ttl(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) in (1, 3):
            return _tool_call_response(name="get_stock_data", args={"ticker": "TSLA"})
        return _structured_response(risk_summary="Fresh result.")

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 223.43, "change_percent": 1.23}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    fake_clock = {"t": 1000.0}
    monkeypatch.setattr(orchestrator.time, "monotonic", lambda: fake_clock["t"])

    asyncio.run(run_research_query("What's Tesla's current stock price?"))
    assert len(calls) == 2

    # Still within the 15-minute TTL — cache hit, no new completion calls.
    fake_clock["t"] += orchestrator.CACHE_TTL_SECONDS - 1
    asyncio.run(run_research_query("What's Tesla's current stock price?"))
    assert len(calls) == 2

    # Past the TTL — the entry is stale, so a fresh pair of calls happens.
    fake_clock["t"] += 2
    asyncio.run(run_research_query("What's Tesla's current stock price?"))
    assert len(calls) == 4


def test_run_research_query_does_not_cache_malformed_output(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        if len(calls) % 3 == 1:
            return _tool_call_response(name="get_stock_data", args={"ticker": "TSLA"})
        return _text_response("not json")

    async def fake_get_stock_data(ticker):
        return {"status": "ok", "ticker": ticker, "price": 223.43, "change_percent": 1.23}

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(orchestrator, "get_stock_data", fake_get_stock_data)

    first = asyncio.run(run_research_query("What's Tesla's current stock price?"))
    assert first["status"] == "malformed_output"
    assert len(calls) == 3  # planning + two bounded synthesis attempts

    # A malformed_output result must NOT have been cached — a second
    # identical query re-runs the full loop, it doesn't get a cached
    # failure handed back.
    second = asyncio.run(run_research_query("What's Tesla's current stock price?"))
    assert second["status"] == "malformed_output"
    assert len(calls) == 6


def test_cached_result_returned_even_without_a_configured_key(monkeypatch):
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return _text_response("The capital of France is Paris.")

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)

    first = asyncio.run(run_research_query("What's the capital of France?"))
    assert first["answer"] == "The capital of France is Paris."

    # Remove the configured key entirely — a cache hit must still succeed,
    # since caching short-circuits before the API-key check.
    monkeypatch.setattr(orchestrator.settings, "anthropic_api_key", "")
    monkeypatch.setattr(orchestrator.settings, "gemini_api_key", "")

    second = asyncio.run(run_research_query("What's the capital of France?"))
    assert second == first
    assert len(calls) == 1  # cache hit — no second completion call at all


def test_cache_sweeps_expired_entries_on_next_write(monkeypatch):
    # Active eviction, not just lazy-on-read: an entry for a query that's
    # never asked again must still get cleaned up once it's expired, by
    # the *next* write to the cache from a completely different query —
    # not left sitting in memory until someone happens to re-ask it.
    async def fake_acompletion(**kwargs):
        return _text_response("An answer.")

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)

    fake_clock = {"t": 1000.0}
    monkeypatch.setattr(orchestrator.time, "monotonic", lambda: fake_clock["t"])

    asyncio.run(run_research_query("Query A"))
    assert "query a" in orchestrator._research_cache

    fake_clock["t"] += orchestrator.CACHE_TTL_SECONDS + 1  # past TTL, nothing re-accessed it

    asyncio.run(run_research_query("Query B"))
    assert "query a" not in orchestrator._research_cache
    assert "query b" in orchestrator._research_cache


def test_cache_evicts_oldest_entries_past_max_size(monkeypatch):
    # The expiry sweep alone doesn't bound memory against a burst of many
    # distinct queries all still within their TTL — CACHE_MAX_ENTRIES is
    # what caps that, FIFO (oldest-inserted first).
    async def fake_acompletion(**kwargs):
        return _text_response("An answer.")

    monkeypatch.setattr(orchestrator.litellm, "acompletion", fake_acompletion)

    fake_clock = {"t": 1000.0}
    monkeypatch.setattr(orchestrator.time, "monotonic", lambda: fake_clock["t"])

    overflow = 5
    total = orchestrator.CACHE_MAX_ENTRIES + overflow
    for i in range(total):
        fake_clock["t"] += 1  # distinct expires_at per entry -> deterministic FIFO order
        asyncio.run(run_research_query(f"Query number {i}"))

    assert len(orchestrator._research_cache) == orchestrator.CACHE_MAX_ENTRIES
    for i in range(overflow):
        assert f"query number {i}" not in orchestrator._research_cache
    assert f"query number {total - 1}" in orchestrator._research_cache


def test_run_research_query_raises_without_a_configured_key(monkeypatch):
    monkeypatch.setattr(orchestrator.settings, "anthropic_api_key", "")
    monkeypatch.setattr(orchestrator.settings, "gemini_api_key", "")

    with pytest.raises(RuntimeError, match="No API key configured"):
        asyncio.run(run_research_query("What's Tesla's current stock price?"))
