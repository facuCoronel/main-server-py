import json
import logging
from typing import Any

from agent_framework import ChatOptions
from agent_framework.openai import OpenAIChatClient

from config import get_settings
from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import SkillDefinition
from src.application.interfaces.ui_generator import UiGeneratorPort
from src.domain.value_objects.intent_type import IntentType
from src.infrastructure.agents.json_utils import extract_json
from src.infrastructure.agents.ollama_chat_client import create_ollama_chat_client
from src.infrastructure.agents.prompts import (
    build_ui_instructions,
    build_ui_user_message,
)

logger = logging.getLogger(__name__)


class AgentFrameworkUiGenerator(UiGeneratorPort):
    """Declarative-UI agent backed by Microsoft Agent Framework over hosted Ollama.

    The agent has NO tools: it works exclusively from the serialized context_pack
    and the validated report. It never returns HTML or EChartsOption.
    """

    def __init__(
        self,
        chat_client: OpenAIChatClient | None = None,
        temperature: float | None = None,
    ) -> None:
        self._client = chat_client or create_ollama_chat_client()
        self._temperature = temperature

    async def generate(
        self,
        question: str,
        intent_type: IntentType,
        skill: SkillDefinition,
        context_pack: ContextPack,
        validated_report: dict[str, Any],
    ) -> dict[str, Any]:
        instructions = build_ui_instructions(skill)
        agent = self._client.as_agent(name="ui-generator", instructions=instructions)

        user_message = build_ui_user_message(question, context_pack, validated_report)

        temperature = (
            self._temperature
            if self._temperature is not None
            else get_settings().business_chat.report_temperature
        )
        response = await agent.run(
            user_message,
            options=ChatOptions(temperature=temperature),
        )

        ui = parse_ui(response.text)
        logger.info("ui generated with keys: %s", list(ui.keys()))
        return ui


def parse_ui(text: str) -> dict[str, Any]:
    raw = extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"content": (text or "").strip()}

    if isinstance(data, dict):
        return data
    return {"content": data}
