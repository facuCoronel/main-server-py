import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.domain.value_objects.capability import CapabilityDescriptor
from src.infrastructure.capabilities.capability_gateway import FastFixProCapabilityGateway

logger = logging.getLogger(__name__)

mcp = FastMCP("main-server-fastfixpro")

# Shared gateway: same catalog + execution rules as the in-process /business-chat pipeline.
_gateway = FastFixProCapabilityGateway()


def _serialize_capabilities(capabilities: list[CapabilityDescriptor]) -> str:
    result = [
        {
            "name": c.id,
            "description": c.description,
            "params": (
                {
                    p.name: {
                        "type": p.type,
                        "required": p.required,
                        "description": p.description,
                    }
                    for p in c.params
                }
                if c.params
                else None
            ),
        }
        for c in capabilities
    ]
    return json.dumps(result, ensure_ascii=False)


@mcp.tool(
    name="list_business_capabilities",
    description=(
        "Returns the catalog of safe GET endpoints exposed by the business system "
        "(FastFixPro.Api). Each capability has a name, description, and optional parameter "
        "definitions. Call this first to discover what data you can retrieve, then use "
        "call_business_capability to execute one."
    ),
)
async def list_business_capabilities() -> str:
    logger.info("[FastFixPro] list_business_capabilities invoked")
    capabilities = await _gateway.discover()
    logger.info(
        "[FastFixPro] list_business_capabilities returning %d capabilities: [%s]",
        len(capabilities),
        ", ".join(c.id for c in capabilities),
    )
    return _serialize_capabilities(capabilities)


@mcp.tool(
    name="call_business_capability",
    description=(
        "Executes a named capability from the business system and returns the data as JSON. "
        "First call list_business_capabilities to know which capabilities are available and "
        "what parameters each requires. The agent cannot supply arbitrary URLs — only "
        "capabilities present in the catalog can be executed."
    ),
)
async def call_business_capability(
    capability_name: str,
    params: str | None = None,
) -> str:
    """capability_name: Exact name from list_business_capabilities, e.g. 'get_api_reports_sales'.

    params: JSON object, e.g. {"month": 4, "year": 2025}. Pass null if no params needed.
    """
    parsed: dict[str, Any] = {}
    if params and params.strip():
        try:
            obj = json.loads(params)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid params JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError('\'params\' must be a JSON object, e.g. {"month": 4}.')
        parsed = obj

    result = await _gateway.execute(capability_name, parsed)
    return json.dumps(result, ensure_ascii=False)
