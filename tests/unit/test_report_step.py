from typing import Any

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.skill import PlannerConfig, ReportConfig, SkillDefinition
from src.application.interfaces.report_generator import ReportGeneratorPort
from src.application.pipeline.report_step import run_report
from src.domain.value_objects.intent_type import IntentType


class FakeReportGenerator(ReportGeneratorPort):
    def __init__(self, report: dict[str, Any]) -> None:
        self._report = report
        self.received: ContextPack | None = None

    async def generate(self, context_pack: ContextPack, skill: SkillDefinition) -> dict[str, Any]:
        self.received = context_pack
        return self._report


def _skill() -> SkillDefinition:
    return SkillDefinition(
        intent_type=IntentType.BUSINESS_REPORT,
        display_name="x",
        description="d",
        planner=PlannerConfig(system_prompt="p"),
        report=ReportConfig(system_prompt="r"),
        output_schema="business_report",
    )


async def test_run_report_delegates_and_passes_context_pack():
    pack = ContextPack(business_context={"intent_type": "business_report"}, available_data={"a": 1})
    gen = FakeReportGenerator({"resumen": "ok"})

    report = await run_report(gen, pack, _skill())

    assert report == {"resumen": "ok"}
    assert gen.received is pack
