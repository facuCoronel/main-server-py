from typing import Any

import httpx

from config import get_settings


class FastFixProClient:
    """HTTP client for the FastFixPro external API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.fastfixpro_api_base_url.rstrip("/")
        self._token = settings.fastfixpro_api_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base_url}{path}",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, body: dict) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def put(self, path: str, body: dict) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self._base_url}{path}",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def delete(self, path: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self._base_url}{path}",
                headers=self._headers(),
            )
            response.raise_for_status()
