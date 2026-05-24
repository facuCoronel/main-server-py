import logging
from typing import Any

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import SkillDefinition
from src.application.interfaces.report_generator import ReportGeneratorPort

logger = logging.getLogger(__name__)


async def run_report(
    generator: ReportGeneratorPort,
    context_pack: ContextPack,
    skill: SkillDefinition,
) -> dict[str, Any]:
    """LLM step: generate the final report from the context pack only (no tools)."""
    report = await generator.generate(context_pack, skill)
    logger.info("report keys: %s", list(report.keys()))
    return report
