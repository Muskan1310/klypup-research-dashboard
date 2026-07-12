"""Scratch/seed script — NOT a migration, NOT a pytest test. Inserts one
Document row per sample filing (backend/data/filings/*.txt) into Postgres,
so the `documents` table (TDD Section 4: RAG ingestion metadata — the
actual chunk vectors live in Chroma, not here) has a record of what's been
ingested. `documents` has no org_id: per TDD Section 4, ingested filings
are shared reference data across tenants, not tenant-owned.

This script only writes the Postgres side. Run app/rag/ingest.py's
ingest_documents() first (or via scripts/run_ingestion.py) to actually
chunk/embed the files into Chroma — this script mirrors that into the
relational side and doesn't touch Chroma itself.

Idempotent: re-running skips any file whose source_path already has a
Document row, rather than inserting a duplicate.

Run from backend/:
    poetry run python scripts/seed_documents.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.models import Document  # noqa: E402
from app.rag.ingest import DATA_DIR, parse_filename  # noqa: E402

if __name__ == "__main__":
    db = SessionLocal()
    try:
        for file_path in sorted(DATA_DIR.glob("*.txt")):
            ticker, doc_type = parse_filename(file_path.name)
            source_path = str(file_path)

            existing = db.query(Document).filter(Document.source_path == source_path).first()
            if existing is not None:
                print(f"Skipping {file_path.name} — Document row already exists (id={existing.id})")
                continue

            document = Document(company_ticker=ticker, doc_type=doc_type, source_path=source_path)
            db.add(document)
            db.commit()
            db.refresh(document)
            print(f"Inserted Document(id={document.id}, ticker={ticker!r}, doc_type={doc_type!r})")
    finally:
        db.close()
