from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.tenant_config import TenantConfig
from src.domain.repositories.tenant_config_repository import ITenantConfigRepository
from src.infrastructure.persistence.postgres.models.tenant_config import TenantConfigModel


class PgTenantConfigRepository(ITenantConfigRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> TenantConfig | None:
        result = await self._session.get(TenantConfigModel, id)
        return _to_entity(result) if result else None

    async def get_by_tenant_name(self, tenant_name: str) -> TenantConfig | None:
        row = await self._session.execute(
            select(TenantConfigModel).where(TenantConfigModel.tenant_name == tenant_name)
        )
        model = row.scalars().first()
        return _to_entity(model) if model else None

    async def get_all(self) -> list[TenantConfig]:
        rows = await self._session.execute(select(TenantConfigModel))
        return [_to_entity(m) for m in rows.scalars().all()]

    async def add(self, config: TenantConfig) -> TenantConfig:
        model = _to_model(config)
        self._session.add(model)
        await self._session.flush()
        return config

    async def update(self, config: TenantConfig) -> TenantConfig:
        model = await self._session.get(TenantConfigModel, config.id)
        if model is None:
            raise ValueError(f"TenantConfig {config.id} not found")
        model.tenant_name = config.tenant_name
        model.mysql_connection_string = config.mysql_connection_string
        model.ollama_api_key = config.ollama_api_key
        await self._session.flush()
        return config

    async def delete(self, id: UUID) -> None:
        model = await self._session.get(TenantConfigModel, id)
        if model:
            await self._session.delete(model)
            await self._session.flush()


def _to_entity(m: TenantConfigModel) -> TenantConfig:
    return TenantConfig(
        id=m.id,
        tenant_name=m.tenant_name,
        mysql_connection_string=m.mysql_connection_string,
        ollama_api_key=m.ollama_api_key,
    )


def _to_model(e: TenantConfig) -> TenantConfigModel:
    return TenantConfigModel(
        id=e.id,
        tenant_name=e.tenant_name,
        mysql_connection_string=e.mysql_connection_string,
        ollama_api_key=e.ollama_api_key,
    )
