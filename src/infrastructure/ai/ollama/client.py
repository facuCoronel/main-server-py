from dataclasses import dataclass

import httpx

from config import get_settings


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class OllamaClient:
    """HTTP client for the Ollama API (compatible with OpenAI chat completions format)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._api_key = settings.ollama_api_key
        self._model = settings.ollama_model

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        payload: dict = {
            "model": model or self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})
        return ChatResponse(
            content=choice["content"],
            model=data.get("model", self._model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        payload = {"model": model or self._model, "input": text}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/v1/embeddings",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data["data"][0]["embedding"]
