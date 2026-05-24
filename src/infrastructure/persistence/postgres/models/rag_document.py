from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.persistence.postgres.base import Base


class RagDocumentModel(Base):
    __tablename__ = "rag_documents"
    __table_args__ = (Index("IX_rag_documents_CreatedAt", "CreatedAt"),)

    id: Mapped[UUID] = mapped_column("Id", PG_UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column("Name", Text, nullable=False)
    source: Mapped[str] = mapped_column("Source", Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column("MetadataJson", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), nullable=False)

    chunks: Mapped[list["RagChunkModel"]] = relationship(  # type: ignore[name-defined]
        "RagChunkModel", back_populates="document", cascade="all, delete-orphan"
    )
