import logging
from typing import Any

from pydantic import ValidationError

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import SkillDefinition
from src.application.dtos.ui_schema import UiSchema
from src.application.interfaces.ui_generator import UiGeneratorPort
from src.domain.value_objects.intent_type import IntentType

logger = logging.getLogger(__name__)


async def run_ui_generation(
    ui_generator: UiGeneratorPort,
    question: str,
    intent_type: IntentType,
    skill: SkillDefinition,
    context_pack: ContextPack,
    validated_report: dict[str, Any],
) -> dict[str, Any] | None:
    """Generate raw declarative UI after the report is validated.

    Returns None when the skill has no `ui` section or `ui.enabled` is False.
    """
    if skill.ui is None or not skill.ui.enabled:
        return None
    return await ui_generator.generate(
        question, intent_type, skill, context_pack, validated_report
    )


def validate_ui_schema(
    raw_ui: dict[str, Any] | None,
    skill: SkillDefinition,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate raw UI against UiSchema (lenient).

    Never raises: on failure returns (None, [warning]) so the request still responds.
    """
    if raw_ui is None:
        return None, []
    try:
        ui = UiSchema.model_validate(raw_ui)
    except ValidationError as exc:
        warning = f"ui generation: schema validation failed: {_format_error(exc)}"
        logger.warning(warning)
        return None, [warning]
    return ui.model_dump(), []


def _format_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)
