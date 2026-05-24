import json
import logging
from typing import Any

import httpx

from config import get_settings
from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.domain.value_objects.capability import CapabilityDescriptor, CapabilityParam
from src.mcp.catalog import CapabilityCatalog, CapabilityDefinition, get_catalog

logger = logging.getLogger(__name__)

_MAX_RESPONSE_KB = 512


class FastFixProCapabilityGateway(CapabilityGatewayPort):
    """In-process gateway over the 2 MCP capabilities, backed by FastFixPro.

    Shares the catalog (and its TTL cache) with the MCP server so both paths enforce
    the same rule: only capabilities present in the catalog can be executed.
    """

    def __init__(self, catalog: CapabilityCatalog | None = None) -> None:
        self._catalog = catalog or get_catalog()

    async def discover(self) -> list[CapabilityDescriptor]:
        definitions = await self._catalog.get()
        return [_to_descriptor(d) for d in definitions]

    async def execute(self, capability_id: str, params: dict[str, Any]) -> Any:
        definitions = await self._catalog.get()
        capability = next(
            (c for c in definitions if c.name.lower() == (capability_id or "").strip().lower()),
            None,
        )
        if capability is None:
            available = ", ".join(c.name for c in definitions)
            logger.warning("Capability '%s' not found. Available: [%s]", capability_id, available)
            raise ValueError(
                f"Capability '{capability_id}' not found in catalog. "
                "Discover capabilities before executing one."
            )

        if capability.method.upper() != "GET":
            raise ValueError(
                f"Capability '{capability_id}' uses method '{capability.method}'. "
                "Only GET capabilities can be executed."
            )

        query = _validate_params(capability, params)

        settings = get_settings()
        base_url = settings.fastfixpro_api_base_url.rstrip("/")
        token = settings.fastfixpro_api_token
        url = f"{base_url}/{capability.path.lstrip('/')}"
        logger.info(
            "Executing capability '%s' → %s (params=%s)", capability_id, url, list(query.keys())
        )

        return await _fetch(url, query, token, capability_id)


def _to_descriptor(d: CapabilityDefinition) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        id=d.name,
        description=d.description,
        params=[
            CapabilityParam(
                name=p.name, type=p.type, required=p.required, description=p.description
            )
            for p in d.parameters
        ],
    )


def _validate_params(capability: CapabilityDefinition, params: dict[str, Any]) -> dict[str, str]:
    known = {p.name for p in capability.parameters}
    query: dict[str, str] = {}
    for key, value in (params or {}).items():
        if key in known:
            query[key] = str(value)
        else:
            logger.debug(
                "Discarding unknown param '%s' for capability '%s'", key, capability.name
            )

    missing = [p.name for p in capability.parameters if p.required and p.name not in query]
    if missing:
        raise ValueError(
            f"Capability '{capability.name}' requires the following parameters: "
            f"{', '.join(missing)}."
        )
    return query


async def _fetch(url: str, query: dict[str, str], token: str, capability_id: str) -> Any:
    max_bytes = _MAX_RESPONSE_KB * 1024
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "GET",
                url,
                params=query or None,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            ) as response:
                if not response.is_success:
                    body = await response.aread()
                    err_text = body.decode(errors="replace")[:400]
                    raise RuntimeError(
                        f"Capability '{capability_id}' returned {response.status_code} "
                        f"{response.reason_phrase}: {err_text}"
                    )

                chunks: list[bytes] = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise RuntimeError(
                            f"Response from capability '{capability_id}' exceeds the "
                            f"{_MAX_RESPONSE_KB} KB limit."
                        )
                    chunks.append(chunk)

        raw = b"".join(chunks).decode()
        logger.info("Capability '%s' returned %d bytes", capability_id, total)
        return _parse_json(raw)

    except (ValueError, RuntimeError):
        raise
    except httpx.RequestError as exc:
        logger.warning("Connection error for capability '%s': %s", capability_id, exc)
        raise RuntimeError(f"HTTP request failed for capability '{capability_id}': {exc}") from exc
    except TimeoutError:
        logger.warning("Timeout for capability '%s'", capability_id)
        raise RuntimeError(f"Capability '{capability_id}' timed out.")


def _parse_json(raw: str) -> Any:
    if not raw or not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_response": raw}
