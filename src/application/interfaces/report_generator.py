from abc import ABC, abstractmethod
from typing import Any

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import SkillDefinition


class ReportGeneratorPort(ABC):
    @abstractmethod
    async def generate(
        self,
        context_pack: ContextPack,
        skill: SkillDefinition,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """Produce the final report from the context pack only (no tools).

        `feedback` carries a validation error from a previous attempt, enabling one repair pass.
        """
        ...
