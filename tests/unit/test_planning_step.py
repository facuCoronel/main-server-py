from src.application.dtos.pipeline import CapabilityPlan
from src.application.dtos.skill import PlannerConfig, ReportConfig, SkillDefinition
from src.application.interfaces.capability_planner import CapabilityPlannerPort
from src.application.pipeline.planning_step import run_planning, validate_plan
from src.domain.value_objects.capability import CapabilityDescriptor
from src.domain.value_objects.capability_plan import CapabilityPlanItem
from src.domain.value_objects.intent_type import IntentType


def _caps() -> list[CapabilityDescriptor]:
    return [
        CapabilityDescriptor(id="get_sales", description="sales"),
        CapabilityDescriptor(id="get_customers", description="customers"),
    ]


def _item(cid: str) -> CapabilityPlanItem:
    return CapabilityPlanItem(capability_id=cid, reason="r", params={})


def test_validate_plan_keeps_only_discovered_ids():
    plan = CapabilityPlan(items=[_item("get_sales"), _item("get_customers")])
    result = validate_plan(plan, _caps(), max_capabilities=8)
    assert [i.capability_id for i in result.plan.items] == ["get_sales", "get_customers"]
    assert result.discarded == []


def test_validate_plan_drops_hallucinated_capability():
    plan = CapabilityPlan(items=[_item("get_sales"), _item("get_invented_endpoint")])
    result = validate_plan(plan, _caps(), max_capabilities=8)
    assert [i.capability_id for i in result.plan.items] == ["get_sales"]
    assert result.discarded == ["get_invented_endpoint"]


def test_validate_plan_caps_to_max_capabilities():
    plan = CapabilityPlan(items=[_item("get_sales"), _item("get_customers")])
    result = validate_plan(plan, _caps(), max_capabilities=1)
    assert [i.capability_id for i in result.plan.items] == ["get_sales"]
    assert result.discarded == []


def test_validate_plan_empty_plan():
    result = validate_plan(CapabilityPlan(items=[]), _caps(), max_capabilities=8)
    assert result.plan.items == []
    assert result.discarded == []


class _FakePlanner(CapabilityPlannerPort):
    def __init__(self, plan: CapabilityPlan) -> None:
        self._plan = plan
        self.calls = 0

    async def plan(self, question, intent_type, skill, capabilities) -> CapabilityPlan:
        self.calls += 1
        return self._plan


def _skill() -> SkillDefinition:
    return SkillDefinition(
        intent_type=IntentType.BUSINESS_REPORT,
        display_name="x",
        description="x",
        planner=PlannerConfig(system_prompt="p"),
        report=ReportConfig(system_prompt="r"),
        output_schema="business_report",
    )


async def test_run_planning_delegates_to_planner():
    expected = CapabilityPlan(items=[_item("get_sales")])
    planner = _FakePlanner(expected)
    result = await run_planning(
        planner, "q", IntentType.BUSINESS_REPORT, _skill(), _caps()
    )
    assert planner.calls == 1
    assert result is expected
