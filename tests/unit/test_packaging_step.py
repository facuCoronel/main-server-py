from src.application.dtos.pipeline import ExecutionResult
from src.application.dtos.skill import PlannerConfig, ReportConfig, SkillDefinition
from src.application.pipeline.packaging_step import build_context_pack
from src.domain.value_objects.capability import ExecutionStatus
from src.domain.value_objects.intent_type import IntentType


def _skill() -> SkillDefinition:
    return SkillDefinition(
        intent_type=IntentType.BUSINESS_REPORT,
        display_name="Reporte de negocio",
        description="d",
        language="es",
        planner=PlannerConfig(system_prompt="p"),
        report=ReportConfig(system_prompt="r"),
        output_schema="business_report",
    )


def test_available_data_contains_only_successes():
    results = [
        ExecutionResult(capability_id="a", status=ExecutionStatus.SUCCESS, data={"x": 1}),
        ExecutionResult(capability_id="b", status=ExecutionStatus.FAILED, error="boom"),
    ]
    pack = build_context_pack(IntentType.BUSINESS_REPORT, "q", _skill(), results)

    assert pack.available_data == {"a": {"x": 1}}
    assert "b" not in pack.available_data


def test_business_context_carries_intent_and_skill_metadata():
    pack = build_context_pack(IntentType.BUSINESS_REPORT, "¿ventas?", _skill(), [])
    assert pack.business_context["intent_type"] == "business_report"
    assert pack.business_context["question"] == "¿ventas?"
    assert pack.business_context["output_schema"] == "business_report"
    assert pack.business_context["language"] == "es"


def test_data_quality_reflects_failures():
    results = [
        ExecutionResult(capability_id="a", status=ExecutionStatus.SUCCESS, data={}),
        ExecutionResult(capability_id="b", status=ExecutionStatus.FAILED, error="x"),
    ]
    pack = build_context_pack(IntentType.BUSINESS_REPORT, "q", _skill(), results)
    assert pack.data_quality.requested == 2
    assert pack.data_quality.succeeded == 1
    assert pack.data_quality.failed_capabilities == ["b"]


def test_empty_results_produce_empty_pack():
    pack = build_context_pack(IntentType.BUSINESS_REPORT, "q", _skill(), [])
    assert pack.available_data == {}
    assert pack.data_quality.requested == 0
    assert pack.data_quality.completeness == 0.0
