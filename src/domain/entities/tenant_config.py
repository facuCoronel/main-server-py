from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class TenantConfig:
    tenant_name: str
    mysql_connection_string: str
    id: UUID = field(default_factory=uuid4)
    ollama_api_key: str | None = None
