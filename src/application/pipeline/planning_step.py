import logging
from dataclasses import dataclass

from src.application.dtos.pipeline import CapabilityPlan
from src.application.dtos.skill import SkillDefinition
from src.application.interfaces.capability_planner import CapabilityPlannerPort
from src.domain.value_objects.capability import CapabilityDescriptor
from src.domain.value_objects.intent_type import IntentType

logger = logging.getLogger(__name__)


@dataclass
class PlanValidation:
    plan: CapabilityPlan
    discarded: list[str]


async def run_planning(
    planner: CapabilityPlannerPort,
    question: str,
    intent_type: IntentType,
    skill: SkillDefinition,
    capabilities: list[CapabilityDescriptor],
) -> CapabilityPlan:
    """LLM step: ask the planner which discovered capabilities to call."""
    return await planner.plan(question, intent_type, skill, capabilities)


def validate_plan(
    plan: CapabilityPlan,
    capabilities: list[CapabilityDescriptor],
    max_capabilities: int,
) -> PlanValidation:
    """Deterministic anti-hallucination gate: drop any capability_id not discovered."""
    valid_ids = {c.id for c in capabilities}
    kept = []
    discarded = []
    for item in plan.items:
        if item.capability_id in valid_ids:
            kept.append(item)
        else:
            discarded.append(item.capability_id)

    if discarded:
        logger.warning("discarded hallucinated capabilities: %s", discarded)

    return PlanValidation(plan=CapabilityPlan(items=kept[:max_capabilities]), discarded=discarded)
