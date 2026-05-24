from typing import Any

from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.application.pipeline.discovery_step import run_discovery
from src.domain.value_objects.capability import CapabilityDescriptor


class FakeGateway(CapabilityGatewayPort):
    def __init__(self, descriptors: list[CapabilityDescriptor]) -> None:
        self._descriptors = descriptors

    async def discover(self) -> list[CapabilityDescriptor]:
        return self._descriptors

    async def execute(self, capability_id: str, params: dict[str, Any]) -> Any:
        raise AssertionError("execute should not be called during discovery")


async def test_run_discovery_returns_capabilities():
    descriptors = [
        CapabilityDescriptor(id="a", description="A"),
        CapabilityDescriptor(id="b", description="B"),
    ]
    result = await run_discovery(FakeGateway(descriptors))
    assert [c.id for c in result] == ["a", "b"]
