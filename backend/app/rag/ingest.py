"""RAG ingestion pipeline (TDD Section 8 step 1): chunk sample filing
documents, embed them, and store them in a persistent local Chroma
collection.

This is the offline/setup half of RAG. The runtime half — similarity
search plus the confidence/quality gate that's this project's stated
differentiator (TDD Section 8 steps 2-3) — is a separate, later module;
this one only prepares the knowledge base.

CLAUDE.md hard constraint #2: Chroma, running locally/embedded — not
pgvector, Pinecone, or FAISS. `chromadb.PersistentClient` writes to
`settings.chroma_persist_dir` on disk, no external service required.

Embeddings use Chroma's built-in default embedding function (a local
sentence-transformers model Chroma downloads and runs itself) rather than
a separate embedding API call (OpenAI, Voyage, Cohere, ...). That's a
deliberate tradeoff, not an oversight: a dedicated embedding API would
likely retrieve somewhat better matches, but it also means a second
API key, a second per-call cost, and a second network dependency on the
retrieval hot path — real complexity for a 5-day assessment whose stated
differentiator is the confidence gate around retrieval, not embedding
quality itself. Revisit this if retrieval quality turns out to be the
actual bottleneck once the confidence gate is built and tested against
real queries.
"""

from pathlib import Path

import chromadb

from app.core.config import settings

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "filings"
COLLECTION_NAME = "filings"

CHUNK_SIZE_WORDS = 500
CHUNK_OVERLAP_WORDS = 50


def ingest_documents() -> list[dict]:
    """Read every `.txt` file in `data/filings/`, chunk it, embed the
    chunks, and upsert them into a persistent Chroma collection.

    Upsert (not add) so re-running ingestion is idempotent — chunk ids are
    deterministic (`"{ticker}-{doc_type}-{chunk_index}"`), so re-ingesting
    the same file overwrites its existing chunks instead of duplicating
    them.

    Returns a per-file summary so callers (the seed script, manual
    verification) know what happened without a separate Chroma query:
        [{"source_path": ..., "ticker": ..., "doc_type": ...,
          "chunk_count": N}, ...]
    """
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    summaries = []
    for file_path in sorted(DATA_DIR.glob("*.txt")):
        ticker, doc_type = parse_filename(file_path.name)
        text = file_path.read_text(encoding="utf-8")
        chunks = _chunk_text(text)

        ids = [f"{ticker}-{doc_type}-{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "ticker": ticker,
                "doc_type": doc_type,
                "source_path": str(file_path),
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]
        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

        summaries.append(
            {
                "source_path": str(file_path),
                "ticker": ticker,
                "doc_type": doc_type,
                "chunk_count": len(chunks),
            }
        )

    return summaries


def parse_filename(filename: str) -> tuple[str, str]:
    """'nvda_sample_filing.txt' -> ('NVDA', '10-K').

    Ticker is the filename's first underscore-separated segment. `doc_type`
    is hardcoded to "10-K" since every current sample file is structured as
    a 10-K-style excerpt (Item 1 / 1A / 7) — this becomes a real parameter
    once ingestion handles more than one document type per company (e.g.
    earnings call transcripts alongside 10-Ks).

    Public (not `_`-prefixed) because scripts/seed_documents.py also needs
    it, to keep the Postgres `documents` row's ticker/doc_type in exact
    sync with what was actually written into Chroma's metadata.
    """
    ticker = filename.split("_")[0].upper()
    return ticker, "10-K"


def _chunk_text(text: str, *, chunk_size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """Sliding-window chunker over whitespace-split words, approximating
    TDD Section 8's "~500 tokens, ~50 token overlap" target by word count
    rather than a real tokenizer.

    Why word count is close enough: English text averages roughly 1.3
    tokens per word across common LLM tokenizers, so 500 words lands
    around 600-700 tokens — in the right neighborhood for the actual goal
    here, which is retrieval precision (chunks small enough to stay
    topically focused, with enough overlap that a fact isn't split exactly
    across a boundary). That goal doesn't need an exact token count, just
    a consistent, reasonable chunk size — so pulling in a tokenizer
    library was unnecessary complexity. It would also have been the wrong
    tokenizer: e.g. tiktoken is OpenAI's, and this project is LLM-provider-
    agnostic (litellm-orchestrator branch) with no single "the" tokenizer
    to target.

    Handles documents shorter than one chunk correctly — returns the whole
    document as a single chunk rather than padding or failing, which is
    exactly what happens for our current sample filings (300-800 words
    each, well within one 500-word chunk for two of the three).
    """
    words = text.split()
    if not words:
        return []

    step = chunk_size - overlap
    chunks = []
    start = 0
    while True:
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
        start += step
    return chunks
