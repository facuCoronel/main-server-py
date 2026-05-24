from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.rag_document import RagDocument


class IRagDocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> RagDocument | None: ...

    @abstractmethod
    async def get_all(self) -> list[RagDocument]: ...

    @abstractmethod
    async def add(self, document: RagDocument) -> RagDocument: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
