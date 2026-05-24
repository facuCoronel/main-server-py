import httpx
import pytest
import respx

from config import get_settings
from src.infrastructure.capabilities.capability_gateway import FastFixProCapabilityGateway
from src.mcp.catalog import ApiParameter, CapabilityDefinition


class FakeCatalog:
    def __init__(self, definitions: list[CapabilityDefinition]) -> None:
        self._definitions = definitions

    async def get(self) -> list[CapabilityDefinition]:
        return self._definitions


def _sales_definition() -> CapabilityDefinition:
    return CapabilityDefinition(
        name="get_sales",
        path="/api/sales",
        method="GET",
        description="Monthly sales",
        parameters=[
            ApiParameter(name="month", location="query", required=True, type="int"),
            ApiParameter(name="year", location="query", required=False, type="int"),
        ],
    )


def _gateway(*definitions: CapabilityDefinition) -> FastFixProCapabilityGateway:
    return FastFixProCapabilityGateway(catalog=FakeCatalog(list(definitions)))


async def test_discover_maps_definitions_to_descriptors():
    gw = _gateway(_sales_definition())
    descriptors = await gw.discover()

    assert len(descriptors) == 1
    d = descriptors[0]
    assert d.id == "get_sales"
    assert d.description == "Monthly sales"
    assert d.required_params == ["month"]


async def test_execute_unknown_capability_raises():
    gw = _gateway(_sales_definition())
    with pytest.raises(ValueError, match="not found"):
        await gw.execute("does_not_exist", {})


async def test_execute_non_get_capability_raises():
    post_cap = CapabilityDefinition(
        name="create_order", path="/api/orders", method="POST", description="create"
    )
    gw = _gateway(post_cap)
    with pytest.raises(ValueError, match="Only GET"):
        await gw.execute("create_order", {})


async def test_execute_missing_required_param_raises():
    gw = _gateway(_sales_definition())
    with pytest.raises(ValueError, match="requires"):
        await gw.execute("get_sales", {"year": 2025})


async def test_execute_success_discards_unknown_params():
    gw = _gateway(_sales_definition())
    base = get_settings().fastfixpro_api_base_url.rstrip("/")

    with respx.mock:
        route = respx.get(f"{base}/api/sales").mock(
            return_value=httpx.Response(200, json={"total": 42})
        )
        result = await gw.execute("get_sales", {"month": 4, "bogus": "x"})

    assert result == {"total": 42}
    assert route.called
    sent = route.calls.last.request
    assert "month=4" in str(sent.url)
    assert "bogus" not in str(sent.url)


async def test_execute_http_error_raises_runtime():
    gw = _gateway(_sales_definition())
    base = get_settings().fastfixpro_api_base_url.rstrip("/")

    with respx.mock:
        respx.get(f"{base}/api/sales").mock(return_value=httpx.Response(500, text="boom"))
        with pytest.raises(RuntimeError, match="500"):
            await gw.execute("get_sales", {"month": 4})
