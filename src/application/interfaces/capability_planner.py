from abc import ABC, abstractmethod

from src.application.dtos.pipeline import CapabilityPlan
from src.application.dtos.skill import SkillDefinition
from src.domain.value_objects.capability import CapabilityDescriptor
from src.domain.value_objects.intent_type import IntentType


class CapabilityPlannerPort(ABC):
    @abstractmethod
    async def plan(
        self,
        question: str,
        intent_type: IntentType,
        skill: SkillDefinition,
        capabilities: list[CapabilityDescriptor],
    ) -> CapabilityPlan:
        """Decide which discovered capabilities to call. Must not invent ids."""
        ...
