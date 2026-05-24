from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.postgres.base import Base


class RagChunkModel(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (
        Index("IX_rag_chunks_ChunkIndex", "ChunkIndex"),
        Index("IX_rag_chunks_DocumentId", "DocumentId"),
        Index(
            "ix_rag_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[UUID] = mapped_column("Id", PG_UUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        "DocumentId", PG_UUID(as_uuid=True), ForeignKey("rag_documents.Id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column("Content", Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column("ChunkIndex", Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), nullable=False)
    embedding: Mapped[list] = mapped_column("embedding", Vector(768), nullable=False)

    document: Mapped["RagDocumentModel"] = relationship(  # type: ignore[name-defined]
        "RagDocumentModel", back_populates="chunks"
    )
