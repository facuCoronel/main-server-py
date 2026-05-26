from abc import ABC, abstractmethod
from typing import Any

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import SkillDefinition
from src.domain.value_objects.intent_type import IntentType


class UiGeneratorPort(ABC):
    @abstractmethod
    async def generate(
        self,
        question: str,
        intent_type: IntentType,
        skill: SkillDefinition,
        context_pack: ContextPack,
        validated_report: dict[str, Any],
    ) -> dict[str, Any]:
        """Produce a declarative UiSchema from the validated report and context pack only.

        No tools, no external systems, no invented data, no HTML/EChartsOption.
        """
        ...
