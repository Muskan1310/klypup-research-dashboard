"""Unit tests for app/rag/ingest.py's pure chunking/parsing helpers.

_chunk_text and parse_filename are pure functions (no I/O, no Chroma, no
network) — cheap and worth verifying directly. ingest_documents() itself
touches the real local Chroma store; it's exercised instead via
scripts/run_ingestion.py's real run (Chroma here is a local embedded DB,
not a rate-limited external API, so there's no cost/quota reason to mock
it in a test the way the HTTP-based tools need mocking).
"""

from app.rag.ingest import _chunk_text, parse_filename


def test_parse_filename_extracts_ticker_and_hardcoded_doc_type():
    assert parse_filename("nvda_sample_filing.txt") == ("NVDA", "10-K")
    assert parse_filename("tsla_sample_filing.txt") == ("TSLA", "10-K")


def test_chunk_text_returns_single_chunk_for_short_text():
    text = " ".join(f"word{i}" for i in range(100))
    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_splits_and_overlaps_for_long_text():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)
    chunks = _chunk_text(text, chunk_size=500, overlap=50)

    # step = chunk_size - overlap = 450; chunks start at word indices
    # 0, 450, 900 -> 3 chunks for 1200 words.
    assert len(chunks) == 3
    assert chunks[0].split()[0] == "word0"
    assert chunks[0].split()[-1] == "word499"
    assert chunks[1].split()[0] == "word450"
    # The last 50 words of chunk 1 are exactly the first 50 words of
    # chunk 2 — this is the ~50-word overlap TDD Section 8 calls for.
    assert chunks[1].split()[:50] == chunks[0].split()[-50:]


def test_chunk_text_handles_empty_text():
    assert _chunk_text("") == []
    assert _chunk_text("   ") == []
