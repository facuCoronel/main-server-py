from abc import ABC, abstractmethod
from typing import Any

from src.domain.value_objects.capability import CapabilityDescriptor


class CapabilityGatewayPort(ABC):
    """Application's view of the 2 MCP capabilities: discover + execute.

    Implementations must guarantee that only discovered capabilities can be executed.
    """

    @abstractmethod
    async def discover(self) -> list[CapabilityDescriptor]:
        ...

    @abstractmethod
    async def execute(self, capability_id: str, params: dict[str, Any]) -> Any:
        ...
