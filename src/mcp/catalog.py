import asyncio
import json
import logging
from typing import Any
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx

from config import get_settings

logger = logging.getLogger(__name__)

_CACHE_TTL = timedelta(minutes=5)


@dataclass
class ApiParameter:
    name: str
    location: str  # "in" field from JSON
    required: bool
    type: str = "string"
    description: str | None = None


@dataclass
class CapabilityDefinition:
    name: str
    path: str
    method: str
    description: str
    parameters: list[ApiParameter] = field(default_factory=list)

    @property
    def required_params(self) -> list[str]:
        return [p.name for p in self.parameters if p.required]


def _parse_capabilities(raw: list[dict[str, Any]]) -> list[CapabilityDefinition]:
    result: list[CapabilityDefinition] = []
    for item in raw:
        params = [
            ApiParameter(
                name=p["name"],
                location=p.get("in", "query"),
                required=p.get("required", False),
                type=p.get("type") or "string",
                description=p.get("description"),
            )
            for p in (item.get("parameters") or [])
        ]
        result.append(
            CapabilityDefinition(
                name=item["name"],
                path=item["path"],
                method=item["method"],
                description=item["description"],
                parameters=params,
            )
        )
    return result


class CapabilityCatalog:
    """In-memory catalog with 5-min TTL, mirrors FastFixProCapabilityCatalog from .NET."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._cache: list[CapabilityDefinition] | None = None
        self._expiry: datetime = datetime.min.replace(tzinfo=UTC)

    async def get(self) -> list[CapabilityDefinition]:
        now = datetime.now(UTC)
        if self._cache is not None and now < self._expiry:
            logger.debug("[FastFixPro] Catalog cache hit (%d capabilities)", len(self._cache))
            return self._cache

        async with self._lock:
            now = datetime.now(UTC)
            if self._cache is not None and now < self._expiry:
                return self._cache

            settings = get_settings()
            base_url = settings.fastfixpro_api_base_url.rstrip("/")
            token = settings.fastfixpro_api_token

            logger.info("[FastFixPro] Fetching capability catalog from %s", base_url)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/api/agent-capabilities",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )

            if not response.is_success:
                raise RuntimeError(
                    f"Failed to fetch capabilities: {response.status_code} {response.reason_phrase}. "
                    "Verify FASTFIXPRO_API_BASE_URL is correct."
                )

            data = response.json()
            raw: list[dict[str, Any]] = data if isinstance(data, list) else data.get("capabilities", [])
            self._cache = _parse_capabilities(raw)
            self._expiry = datetime.now(UTC) + _CACHE_TTL
            logger.info("[FastFixPro] Catalog loaded: %d capabilities", len(self._cache))
            return self._cache

    def invalidate(self) -> None:
        self._cache = None
        self._expiry = datetime.min.replace(tzinfo=UTC)


# Module-level singleton shared across tool invocations
_catalog = CapabilityCatalog()


def get_catalog() -> CapabilityCatalog:
    return _catalog
