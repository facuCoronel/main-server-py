from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.rag_chunk import RagChunk


class IRagChunkRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> RagChunk | None: ...

    @abstractmethod
    async def get_by_document_id(self, document_id: UUID) -> list[RagChunk]: ...

    @abstractmethod
    async def add_many(self, chunks: list[RagChunk]) -> None: ...

    @abstractmethod
    async def similarity_search(self, embedding: list[float], top_k: int) -> list[RagChunk]: ...

    @abstractmethod
    async def delete_by_document_id(self, document_id: UUID) -> None: ...
