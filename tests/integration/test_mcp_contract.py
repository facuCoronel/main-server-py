import json
from typing import Any

import pytest

import src.mcp.server as server
from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.domain.value_objects.capability import CapabilityDescriptor, CapabilityParam


class FakeGateway(CapabilityGatewayPort):
    async def discover(self) -> list[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                id="get_sales",
                description="Monthly sales",
                params=[CapabilityParam(name="month", type="int", required=True)],
            )
        ]

    async def execute(self, capability_id: str, params: dict[str, Any]) -> Any:
        return {"echo_id": capability_id, "params": params}


@pytest.fixture(autouse=True)
def _patch_gateway(monkeypatch):
    monkeypatch.setattr(server, "_gateway", FakeGateway())


async def test_list_business_capabilities_shape():
    out = json.loads(await server.list_business_capabilities())
    assert out == [
        {
            "name": "get_sales",
            "description": "Monthly sales",
            "params": {"month": {"type": "int", "required": True, "description": None}},
        }
    ]


async def test_call_business_capability_parses_params():
    out = json.loads(await server.call_business_capability("get_sales", '{"month": 4}'))
    assert out == {"echo_id": "get_sales", "params": {"month": 4}}


async def test_call_business_capability_no_params():
    out = json.loads(await server.call_business_capability("get_sales"))
    assert out == {"echo_id": "get_sales", "params": {}}


async def test_call_business_capability_invalid_json_raises():
    with pytest.raises(ValueError, match="Invalid params JSON"):
        await server.call_business_capability("get_sales", "not-json")
