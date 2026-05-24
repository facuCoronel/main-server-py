import logging

from src.application.dtos.pipeline import ContextPack, DataQuality, ExecutionResult
from src.application.dtos.skill import SkillDefinition
from src.domain.value_objects.capability import ExecutionStatus
from src.domain.value_objects.intent_type import IntentType

logger = logging.getLogger(__name__)


def build_context_pack(
    intent_type: IntentType,
    question: str,
    skill: SkillDefinition,
    results: list[ExecutionResult],
) -> ContextPack:
    """Deterministic transform from raw execution results into a clean context pack.

    Only successful results are exposed as available_data; failures are reflected in data_quality.
    """
    available_data = {
        r.capability_id: r.data for r in results if r.status == ExecutionStatus.SUCCESS
    }
    data_quality = DataQuality.from_results(results)
    business_context = {
        "intent_type": intent_type.value,
        "question": question,
        "skill": skill.display_name,
        "output_schema": skill.output_schema,
        "language": skill.language,
    }

    logger.info(
        "context pack: %d data sources, completeness=%.2f",
        len(available_data),
        data_quality.completeness,
    )
    return ContextPack(
        business_context=business_context,
        available_data=available_data,
        data_quality=data_quality,
    )
