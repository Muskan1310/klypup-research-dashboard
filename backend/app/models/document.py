"""Document — RAG ingestion metadata only. The actual chunk embeddings live
in Chroma; this row is what lets us map a Chroma hit's metadata back to a
human-readable source (ticker, doc type, file path) for `report_sources`
attribution. Per TDD Section 4, this table has no org_id: the ingested
filings/reports are a shared knowledge base across tenants, not
tenant-owned data.
"""

from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
