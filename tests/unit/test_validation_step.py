from typing import Any

import pytest

from src.application.dtos.pipeline import ContextPack
from src.application.dtos.report_schemas import BusinessReportOutput
from src.application.dtos.skill import PlannerConfig, ReportConfig, SkillDefinition
from src.application.errors import OutputValidationError
from src.application.interfaces.report_generator import ReportGeneratorPort
from src.application.pipeline.validation_step import (
    resolve_output_model,
    validate_and_repair,
    validate_output,
)
from src.domain.value_objects.intent_type import IntentType

VALID_REPORT = {
    "resumen": "r",
    "hallazgos": "h",
    "recomendaciones": "rec",
    "limitations": "",
}


def _skill() -> SkillDefinition:
    return SkillDefinition(
        intent_type=IntentType.BUSINESS_REPORT,
        display_name="x",
        description="d",
        planner=PlannerConfig(system_prompt="p"),
        report=ReportConfig(system_prompt="r"),
        output_schema="business_report",
    )


class ScriptedReportGenerator(ReportGeneratorPort):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = responses
        self.feedbacks: list[str | None] = []

    async def generate(self, context_pack, skill, feedback=None) -> dict[str, Any]:
        self.feedbacks.append(feedback)
        return self._responses.pop(0)


def test_resolve_known_schema():
    assert resolve_output_model("business_report") is BusinessReportOutput


def test_resolve_unknown_schema_raises():
    with pytest.raises(OutputValidationError):
        resolve_output_model("does_not_exist")


def test_validate_output_valid_normalizes_and_strips_extras():
    report = {**VALID_REPORT, "extra": "dropped"}
    result = validate_output(report, BusinessReportOutput)
    assert result.valid
    assert "extra" not in result.report
    assert result.report["resumen"] == "r"


def test_validate_output_invalid_reports_error():
    result = validate_output({"resumen": "only"}, BusinessReportOutput)
    assert not result.valid
    assert result.error is not None and "hallazgos" in result.error


async def test_validate_and_repair_valid_first_does_not_call_generator():
    gen = ScriptedReportGenerator([])  # would raise if called
    out = await validate_and_repair(gen, VALID_REPORT, ContextPack(), _skill())
    assert out["resumen"] == "r"
    assert gen.feedbacks == []


async def test_validate_and_repair_repairs_on_second_attempt():
    gen = ScriptedReportGenerator([VALID_REPORT])
    invalid_first = {"resumen": "missing the rest"}
    out = await validate_and_repair(gen, invalid_first, ContextPack(), _skill())
    assert out["hallazgos"] == "h"
    # repair was called once, with the validation error as feedback
    assert len(gen.feedbacks) == 1
    assert gen.feedbacks[0] is not None and "hallazgos" in gen.feedbacks[0]


async def test_validate_and_repair_raises_when_repair_also_fails():
    gen = ScriptedReportGenerator([{"resumen": "still bad"}])
    with pytest.raises(OutputValidationError):
        await validate_and_repair(gen, {"resumen": "bad"}, ContextPack(), _skill())
