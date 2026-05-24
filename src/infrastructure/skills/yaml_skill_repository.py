import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.application.dtos.skill import SkillDefinition
from src.application.errors import SkillNotFound
from src.application.interfaces.skill_repository import SkillRepositoryPort
from src.domain.value_objects.intent_type import IntentType

logger = logging.getLogger(__name__)


class YamlSkillRepository(SkillRepositoryPort):
    """Loads skills from local YAML files, one per intent_type, cached in memory."""

    def __init__(self, skills_dir: str | Path) -> None:
        self._skills_dir = Path(skills_dir)
        self._cache: dict[IntentType, SkillDefinition] = {}

    async def get(self, intent_type: IntentType) -> SkillDefinition:
        if intent_type in self._cache:
            return self._cache[intent_type]

        path = self._skills_dir / f"{intent_type.value}.yaml"
        if not path.is_file():
            logger.warning("Skill file not found for intent '%s' at %s", intent_type.value, path)
            raise SkillNotFound(intent_type.value)

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        try:
            skill = SkillDefinition.model_validate(raw)
        except ValidationError as exc:
            raise SkillNotFound(intent_type.value) from exc

        if skill.intent_type != intent_type:
            raise SkillNotFound(intent_type.value)

        self._cache[intent_type] = skill
        return skill
