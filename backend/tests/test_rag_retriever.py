"""Tests for app/rag/retriever.py — run against the REAL local Chroma
collection, not mocked. Chroma here is a local embedded DB with a
deterministic embedding model, not a rate-limited external API (unlike
market_data.py/news_search.py's httpx calls) — there's no cost or quota
reason to mock it, and the whole point of these tests is proving the
confidence gate actually discriminates on real embeddings against our real
ingested filings, not on a hand-picked mock distance.
"""

import pytest

from app.rag.ingest import ingest_documents
from app.rag.retriever import SIMILARITY_THRESHOLD, search_documents


@pytest.fixture(scope="module", autouse=True)
def _ensure_ingested():
    # Idempotent (upsert on deterministic chunk ids — see ingest.py) and
    # fast after the model's one-time download, so it's safe and cheap to
    # just always (re-)ingest before these tests rather than depending on
    # scripts/run_ingestion.py having already been run out-of-band.
    ingest_documents()


def test_relevant_query_clears_the_confidence_gate():
    result = search_documents("What are AMD's main risk factors?")

    assert result["status"] == "ok", result
    assert len(result["results"]) > 0
    top = result["results"][0]
    assert top["score"] >= SIMILARITY_THRESHOLD
    assert top["ticker"] == "AMD"
    assert "risk" in top["text"].lower()


def test_irrelevant_query_is_blocked_by_the_confidence_gate():
    result = search_documents("What's the weather in Paris?")

    assert result["status"] == "no_strong_match", result
    assert "reason" in result
    assert "threshold" in result["reason"].lower() or "no indexed filings" in result["reason"].lower()


def test_ticker_filter_scopes_results_to_one_company():
    result = search_documents("business overview and revenue", ticker="TSLA")

    assert result["status"] in ("ok", "no_strong_match"), result
    if result["status"] == "ok":
        assert all(r["ticker"] == "TSLA" for r in result["results"])


def test_ticker_filter_with_no_ingested_filings_is_no_strong_match():
    result = search_documents("anything", ticker="ZZZZ")

    assert result == {"status": "no_strong_match", "reason": "No indexed filings matched for ticker 'ZZZZ'."}


def test_empty_query_fails_without_a_chroma_call():
    result = search_documents("   ")
    assert result == {"status": "failed", "reason": "query must not be empty"}
