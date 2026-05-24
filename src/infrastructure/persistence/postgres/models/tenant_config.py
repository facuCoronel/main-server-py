from uuid import UUID

from sqlalchemy import Index, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.postgres.base import Base


class TenantConfigModel(Base):
    __tablename__ = "tenant_configs"
    __table_args__ = (Index("IX_tenant_configs_TenantName", "TenantName"),)

    id: Mapped[UUID] = mapped_column("Id", PG_UUID(as_uuid=True), primary_key=True)
    tenant_name: Mapped[str] = mapped_column("TenantName", Text, nullable=False)
    mysql_connection_string: Mapped[str] = mapped_column("MySqlConnectionString", Text, nullable=False)
    ollama_api_key: Mapped[str | None] = mapped_column("OllamaApiKey", Text, nullable=True)
