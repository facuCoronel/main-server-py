import json
import logging

from agent_framework import ChatOptions
from agent_framework.openai import OpenAIChatClient
from pydantic import ValidationError

from config import get_settings
from src.application.dtos.pipeline import CapabilityPlan
from src.application.dtos.skill import SkillDefinition
from src.application.errors import PlanningError
from src.application.interfaces.capability_planner import CapabilityPlannerPort
from src.domain.value_objects.capability import CapabilityDescriptor
from src.domain.value_objects.intent_type import IntentType
from src.infrastructure.agents.json_utils import extract_json
from src.infrastructure.agents.ollama_chat_client import create_ollama_chat_client
from src.infrastructure.agents.prompts import (
    build_planner_instructions,
    build_planner_user_message,
)

logger = logging.getLogger(__name__)


class AgentFrameworkPlanner(CapabilityPlannerPort):
    """Planner backed by Microsoft Agent Framework over the hosted Ollama model.

    The agent has NO tools bound: it only reasons over the serialized capability catalog
    and returns a structured plan (parsed and validated defensively).
    """

    def __init__(
        self,
        chat_client: OpenAIChatClient | None = None,
        temperature: float | None = None,
    ) -> None:
        self._client = chat_client or create_ollama_chat_client()
        self._temperature = temperature

    async def plan(
        self,
        question: str,
        intent_type: IntentType,
        skill: SkillDefinition,
        capabilities: list[CapabilityDescriptor],
    ) -> CapabilityPlan:
        instructions = build_planner_instructions(skill, capabilities)
        agent = self._client.as_agent(name="capability-planner", instructions=instructions)

        temperature = (
            self._temperature
            if self._temperature is not None
            else get_settings().business_chat.planner_temperature
        )
        response = await agent.run(
            build_planner_user_message(question, intent_type),
            options=ChatOptions(temperature=temperature),
        )

        plan = parse_plan(response.text)
        logger.info("planner proposed %d capabilities", len(plan.items))
        return plan


def parse_plan(text: str) -> CapabilityPlan:
    raw = extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PlanningError(f"Planner did not return valid JSON: {exc}") from exc

    if isinstance(data, list):
        data = {"items": data}
    if not isinstance(data, dict):
        raise PlanningError("Planner JSON must be an object or a list of plan items.")
    data.setdefault("items", [])

    try:
        return CapabilityPlan.model_validate(data)
    except ValidationError as exc:
        raise PlanningError(f"Planner JSON does not match the plan schema: {exc}") from exc
