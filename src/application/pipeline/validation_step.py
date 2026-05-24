import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.report_schemas import OUTPUT_SCHEMAS
from src.application.dtos.skill import SkillDefinition
from src.application.errors import OutputValidationError
from src.application.interfaces.report_generator import ReportGeneratorPort

logger = logging.getLogger(__name__)


@dataclass
class OutputValidation:
    valid: bool
    report: dict[str, Any]
    error: str | None


def resolve_output_model(output_schema: str) -> type[BaseModel]:
    model = OUTPUT_SCHEMAS.get(output_schema)
    if model is None:
        raise OutputValidationError(f"Unknown output_schema '{output_schema}'.")
    return model


def validate_output(report: dict[str, Any], model: type[BaseModel]) -> OutputValidation:
    try:
        validated = model.model_validate(report)
    except ValidationError as exc:
        return OutputValidation(valid=False, report=report, error=_format_error(exc))
    return OutputValidation(valid=True, report=validated.model_dump(), error=None)


async def validate_and_repair(
    generator: ReportGeneratorPort,
    report: dict[str, Any],
    context_pack: ContextPack,
    skill: SkillDefinition,
) -> dict[str, Any]:
    """Validate the report; on failure, attempt exactly one repair, then raise if still invalid."""
    model = resolve_output_model(skill.output_schema)

    result = validate_output(report, model)
    if result.valid:
        return result.report

    logger.warning("report failed validation, attempting one repair: %s", result.error)
    repaired = await generator.generate(context_pack, skill, feedback=result.error)
    result = validate_output(repaired, model)
    if result.valid:
        return result.report

    raise OutputValidationError(f"Report failed validation after repair: {result.error}")


def _format_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)
