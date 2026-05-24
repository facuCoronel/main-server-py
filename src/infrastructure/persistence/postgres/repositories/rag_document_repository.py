from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.rag_document import RagDocument
from src.domain.repositories.rag_document_repository import IRagDocumentRepository
from src.infrastructure.persistence.postgres.models.rag_document import RagDocumentModel


class PgRagDocumentRepository(IRagDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> RagDocument | None:
        result = await self._session.get(RagDocumentModel, id)
        return _to_entity(result) if result else None

    async def get_all(self) -> list[RagDocument]:
        rows = await self._session.execute(select(RagDocumentModel))
        return [_to_entity(m) for m in rows.scalars().all()]

    async def add(self, document: RagDocument) -> RagDocument:
        model = _to_model(document)
        self._session.add(model)
        await self._session.flush()
        return document

    async def delete(self, id: UUID) -> None:
        model = await self._session.get(RagDocumentModel, id)
        if model:
            await self._session.delete(model)
            await self._session.flush()


def _to_entity(m: RagDocumentModel) -> RagDocument:
    return RagDocument(
        id=m.id,
        name=m.name,
        source=m.source,
        metadata_json=m.metadata_json,
        created_at=m.created_at,
    )


def _to_model(e: RagDocument) -> RagDocumentModel:
    return RagDocumentModel(
        id=e.id,
        name=e.name,
        source=e.source,
        metadata_json=e.metadata_json,
        created_at=e.created_at,
    )
