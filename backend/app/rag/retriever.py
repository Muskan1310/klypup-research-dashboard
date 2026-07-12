"""RAG retrieval tool (TDD Section 8 steps 2-3): queries the Chroma
collection ingest.py populates, with a confidence/quality gate — the
project's stated RAG differentiator (CLAUDE.md hard constraint #8).

Distance metric — verified empirically against the live collection, not
assumed: Chroma's default `hnsw:space` is **"l2" (squared Euclidean
distance), not cosine** — a common wrong assumption. Confirmed via
`collection.configuration_json["hnsw"]["space"] == "l2"`; ingest.py doesn't
pass an explicit `hnsw:space` override, so Chroma's default applies.
Chroma's default embedding function (all-MiniLM-L6-v2) produces
unit-normalized vectors — also verified empirically (L2 norm == 1.0 on
real stored embeddings), which means squared L2 distance and cosine
similarity are related by a fixed identity for any two unit vectors a, b:

    ||a - b||^2 = ||a||^2 + ||b||^2 - 2(a . b) = 2 - 2*cos_sim(a, b)
    =>  cos_sim(a, b) = 1 - (l2_squared_distance / 2)

So we convert Chroma's raw l2 distance into a cosine-similarity-equivalent
score here, rather than exposing raw l2 distance as "the similarity score"
(wrong direction — l2 distance is smaller-is-better, a similarity score
should be bigger-is-better) or silently assuming the collection uses
cosine space (it doesn't). This conversion is specifically tied to the
embeddings being unit-normalized: if the embedding function ever changes
to one that doesn't normalize, or the collection is recreated with a
different `hnsw:space`, this formula needs revisiting alongside it.

Comparison direction: HIGHER score = MORE similar. The confidence gate
below checks `top_score >= SIMILARITY_THRESHOLD`, not `<=`.
"""

import chromadb

from app.core.config import settings
from app.rag.ingest import COLLECTION_NAME

TOP_K = 3

# Threshold is in cosine-similarity-equivalent terms (see module docstring
# for the conversion): 0.0 is the mathematical "no relation" point
# (orthogonal embeddings), 1.0 is identical. 0.2 sits meaningfully above
# that zero point — requiring genuine positive semantic relatedness, not
# just "not exactly unrelated." Empirically, against our 3 ingested
# filings: "What are AMD's main risk factors?" (on-topic) scored ~0.32 top
# similarity; "What's the weather in Paris?" (off-topic) scored ~0.08.
# 0.2 isn't fit to the exact midpoint of those two numbers — that would
# overfit to two anecdotal queries on a 4-chunk corpus — it's grounded in
# the embedding space's own zero point, with the empirical gap serving as
# *confirmation* the choice discriminates correctly, not as the basis for
# the number itself.
SIMILARITY_THRESHOLD = 0.2


def search_documents(query: str, ticker: str | None = None) -> dict:
    """Search the ingested filings for the `TOP_K` chunks most similar to
    `query`, optionally restricted to one company's filings via `ticker`.

    Returns, if the top result clears the confidence gate:
        {
            "status": "ok",
            "results": [
                {"score": 0.316, "text": "...", "ticker": "AMD",
                 "doc_type": "10-K", "source_path": "...", "chunk_index": 0},
                ...
            ],
        }
    `results` is sorted most-similar first (Chroma's own query order).

    Returns, if the top result's similarity is below `SIMILARITY_THRESHOLD`
    — TDD Section 8 point 3, the confidence/quality gate — or if nothing
    at all matched (e.g. a `ticker` filter with no ingested filings):
        {"status": "no_strong_match", "reason": "<human-readable explanation>"}
    This is what stops the synthesis step from treating a weak match as
    reliable ground truth, per CLAUDE.md hard constraint #8: never build
    naive top-k-always-trusted RAG.

    Returns, on ANY failure (empty query, Chroma/embedding error):
        {"status": "failed", "reason": "<human-readable explanation>"}

    Never raises.
    """
    text = query.strip()
    if not text:
        return {"status": "failed", "reason": "query must not be empty"}

    where = {"ticker": ticker.strip().upper()} if ticker else None

    try:
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        collection = client.get_or_create_collection(name=COLLECTION_NAME)
        raw = collection.query(query_texts=[text], n_results=TOP_K, where=where)
    except Exception as exc:
        # Chroma/onnxruntime don't expose a small, well-documented
        # exception hierarchy the way httpx does (see market_data.py /
        # news_search.py, which catch specific httpx exception types) —
        # this broad catch is the single boundary converting any
        # embedding/index failure into our structured {"status": "failed"}
        # shape, matching this function's "never raises" contract.
        return {"status": "failed", "reason": f"Document search failed: {exc}"}

    ids = raw.get("ids") or [[]]
    if not ids[0]:
        scope = f" for ticker {ticker!r}" if ticker else ""
        return {"status": "no_strong_match", "reason": f"No indexed filings matched{scope}."}

    results = [
        {
            "score": round(_distance_to_similarity(distance), 4),
            "text": document,
            "ticker": metadata.get("ticker"),
            "doc_type": metadata.get("doc_type"),
            "source_path": metadata.get("source_path"),
            "chunk_index": metadata.get("chunk_index"),
        }
        for document, metadata, distance in zip(
            raw["documents"][0], raw["metadatas"][0], raw["distances"][0], strict=True
        )
    ]

    top_score = results[0]["score"]
    if top_score < SIMILARITY_THRESHOLD:
        return {
            "status": "no_strong_match",
            "reason": (
                f"Best match similarity {top_score:.3f} is below the "
                f"{SIMILARITY_THRESHOLD} confidence threshold — no strong "
                "match found in the knowledge base for this query."
            ),
        }

    return {"status": "ok", "results": results}


def _distance_to_similarity(l2_squared_distance: float) -> float:
    """Convert Chroma's raw l2 (squared Euclidean) distance into a
    cosine-similarity-equivalent score. See module docstring for the
    derivation and the unit-normalized-embeddings assumption it relies on.
    """
    return 1.0 - (l2_squared_distance / 2.0)
