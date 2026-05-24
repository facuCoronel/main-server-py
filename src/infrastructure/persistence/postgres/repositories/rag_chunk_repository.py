from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.rag_chunk import RagChunk
from src.domain.repositories.rag_chunk_repository import IRagChunkRepository
from src.infrastructure.persistence.postgres.models.rag_chunk import RagChunkModel


class PgRagChunkRepository(IRagChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> RagChunk | None:
        result = await self._session.get(RagChunkModel, id)
        return _to_entity(result) if result else None

    async def get_by_document_id(self, document_id: UUID) -> list[RagChunk]:
        rows = await self._session.execute(
            select(RagChunkModel)
            .where(RagChunkModel.document_id == document_id)
            .order_by(RagChunkModel.chunk_index)
        )
        return [_to_entity(m) for m in rows.scalars().all()]

    async def add_many(self, chunks: list[RagChunk]) -> None:
        models = [_to_model(c) for c in chunks]
        self._session.add_all(models)
        await self._session.flush()

    async def similarity_search(self, embedding: list[float], top_k: int) -> list[RagChunk]:
        # cosine distance via pgvector <=> operator
        rows = await self._session.execute(
            select(RagChunkModel)
            .order_by(RagChunkModel.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        return [_to_entity(m) for m in rows.scalars().all()]

    async def delete_by_document_id(self, document_id: UUID) -> None:
        await self._session.execute(
            delete(RagChunkModel).where(RagChunkModel.document_id == document_id)
        )
        await self._session.flush()


def _to_entity(m: RagChunkModel) -> RagChunk:
    return RagChunk(
        id=m.id,
        document_id=m.document_id,
        content=m.content,
        chunk_index=m.chunk_index,
        created_at=m.created_at,
        embedding=list(m.embedding),
    )


def _to_model(e: RagChunk) -> RagChunkModel:
    return RagChunkModel(
        id=e.id,
        document_id=e.document_id,
        content=e.content,
        chunk_index=e.chunk_index,
        created_at=e.created_at,
        embedding=e.embedding,
    )
