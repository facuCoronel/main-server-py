from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.tenant_config import TenantConfig


class ITenantConfigRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> TenantConfig | None: ...

    @abstractmethod
    async def get_by_tenant_name(self, tenant_name: str) -> TenantConfig | None: ...

    @abstractmethod
    async def get_all(self) -> list[TenantConfig]: ...

    @abstractmethod
    async def add(self, config: TenantConfig) -> TenantConfig: ...

    @abstractmethod
    async def update(self, config: TenantConfig) -> TenantConfig: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
