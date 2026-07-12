"""Runs the RAG ingestion pipeline for real — chunks, embeds, and stores
backend/data/filings/*.txt into the persistent Chroma collection at
settings.chroma_persist_dir. Not a pytest test; run directly, once (or
whenever the sample filings change).

Run from backend/:
    poetry run python scripts/run_ingestion.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.ingest import ingest_documents  # noqa: E402

if __name__ == "__main__":
    summaries = ingest_documents()
    print("Ingestion complete:\n")
    for summary in summaries:
        print(
            f"  {summary['ticker']} ({summary['doc_type']}): "
            f"{summary['chunk_count']} chunk(s) — {summary['source_path']}"
        )
