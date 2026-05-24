from abc import ABC, abstractmethod

from src.application.dtos.skill import SkillDefinition
from src.domain.value_objects.intent_type import IntentType


class SkillRepositoryPort(ABC):
    @abstractmethod
    async def get(self, intent_type: IntentType) -> SkillDefinition:
        """Resolve the skill for an intent. Raises SkillNotFound if absent."""
        ...
