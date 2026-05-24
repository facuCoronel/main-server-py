from agent_framework.openai import OpenAIChatClient

from config import get_settings


def create_ollama_chat_client() -> OpenAIChatClient:
    """Build an OpenAI-compatible chat client pointed at the hosted Ollama endpoint.

    Credentials come from settings (.env) — never hardcoded.
    """
    settings = get_settings()
    base_url = settings.ollama_base_url.rstrip("/")
    return OpenAIChatClient(
        model=settings.ollama_model,
        api_key=settings.ollama_api_key,
        base_url=f"{base_url}/v1",
    )
