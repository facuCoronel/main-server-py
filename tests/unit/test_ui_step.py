from typing import Any

import pytest

from src.application.dtos.skill import (
    PlannerConfig,
    ReportConfig,
    SkillDefinition,
    UiConfig,
)
from src.application.pipeline.ui_step import run_ui_generation, validate_ui_schema
from src.domain.value_objects.intent_type import IntentType


def _skill(ui: UiConfig | None) -> SkillDefinition:
    return SkillDefinition(
        intent_type=IntentType.BUSINESS_REPORT,
        display_name="x",
        description="x",
        planner=PlannerConfig(system_prompt="p"),
        report=ReportConfig(system_prompt="r"),
        output_schema="business_report",
        ui=ui,
    )


class _FakeUiGenerator:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.called = False

    async def generate(self, question, intent_type, skill, context_pack, validated_report):
        self.called = True
        return self.result


@pytest.mark.asyncio
async def test_run_ui_generation_returns_none_when_no_ui():
    gen = _FakeUiGenerator({"layout": "x", "components": []})
    result = await run_ui_generation(
        gen, "q", IntentType.BUSINESS_REPORT, _skill(None), object(), {}
    )
    assert result is None
    assert gen.called is False


@pytest.mark.asyncio
async def test_run_ui_generation_returns_none_when_disabled():
    gen = _FakeUiGenerator({"layout": "x", "components": []})
    result = await run_ui_generation(
        gen, "q", IntentType.BUSINESS_REPORT, _skill(UiConfig(enabled=False)), object(), {}
    )
    assert result is None
    assert gen.called is False


@pytest.mark.asyncio
async def test_run_ui_generation_calls_generator_when_enabled():
    payload = {"layout": "executive_dashboard", "components": []}
    gen = _FakeUiGenerator(payload)
    result = await run_ui_generation(
        gen, "q", IntentType.BUSINESS_REPORT, _skill(UiConfig(enabled=True)), object(), {}
    )
    assert result == payload
    assert gen.called is True


def test_validate_ui_schema_none_returns_none():
    ui, warnings = validate_ui_schema(None, _skill(UiConfig(enabled=True)))
    assert ui is None
    assert warnings == []


def test_validate_ui_schema_valid():
    raw = {
        "layout": "executive_dashboard",
        "components": [{"id": "c1", "type": "metric_card", "title": "T", "value": 5}],
    }
    ui, warnings = validate_ui_schema(raw, _skill(UiConfig(enabled=True)))
    assert warnings == []
    assert ui["layout"] == "executive_dashboard"
    assert ui["components"][0]["value"] == 5  # extra field preserved (lenient)


def test_validate_ui_schema_unknown_type_yields_none_and_warning():
    raw = {"components": [{"id": "c1", "type": "totally_invalid"}]}
    ui, warnings = validate_ui_schema(raw, _skill(UiConfig(enabled=True)))
    assert ui is None
    assert len(warnings) == 1
    assert "ui generation" in warnings[0]
