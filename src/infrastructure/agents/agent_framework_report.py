import json
import logging
from typing import Any

from agent_framework import ChatOptions
from agent_framework.openai import OpenAIChatClient

from config import get_settings
from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import SkillDefinition
from src.application.interfaces.report_generator import ReportGeneratorPort
from src.infrastructure.agents.json_utils import extract_json
from src.infrastructure.agents.ollama_chat_client import create_ollama_chat_client
from src.infrastructure.agents.prompts import (
    build_report_instructions,
    build_report_user_message,
)

logger = logging.getLogger(__name__)


class AgentFrameworkReportGenerator(ReportGeneratorPort):
    """Final report agent backed by Microsoft Agent Framework over hosted Ollama.

    The agent has NO tools: it works exclusively from the serialized context_pack.
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
        context_pack: ContextPack,
        skill: SkillDefinition,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        instructions = build_report_instructions(skill)
        agent = self._client.as_agent(name="report-generator", instructions=instructions)

        user_message = build_report_user_message(context_pack)
        if feedback:
            user_message += (
                f"\n\nYour previous response was invalid: {feedback}\n"
                "Return corrected JSON containing all required keys."
            )

        temperature = (
            self._temperature
            if self._temperature is not None
            else get_settings().business_chat.report_temperature
        )
        response = await agent.run(
            user_message,
            options=ChatOptions(temperature=temperature),
        )

        report = parse_report(response.text)
        logger.info("report generated with keys: %s", list(report.keys()))
        return report


def parse_report(text: str) -> dict[str, Any]:
    raw = extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"content": (text or "").strip()}

    if isinstance(data, dict):
        return data
    return {"content": data}
