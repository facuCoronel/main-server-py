from typing import Any

import pytest
from fastapi.testclient import TestClient

from main import app
from src.api.dependencies import (
    get_capability_gateway,
    get_capability_planner,
    get_report_generator,
    get_skill_repository,
    get_ui_generator,
)
from src.application.dtos.pipeline import CapabilityPlan
from src.application.errors import PlanningError
from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.application.interfaces.capability_planner import CapabilityPlannerPort
from src.application.interfaces.report_generator import ReportGeneratorPort
from src.application.interfaces.ui_generator import UiGeneratorPort
from src.domain.value_objects.capability import CapabilityDescriptor
from src.domain.value_objects.capability_plan import CapabilityPlanItem
from src.infrastructure.skills.yaml_skill_repository import YamlSkillRepository

client = TestClient(app)


class FakeGateway(CapabilityGatewayPort):
    def __init__(self, fail_ids: set[str] | None = None) -> None:
        self.fail_ids = fail_ids or set()

    async def discover(self) -> list[CapabilityDescriptor]:
        return [CapabilityDescriptor(id="get_sales", description="Monthly sales")]

    async def execute(self, capability_id: str, params: dict[str, Any]) -> Any:
        if capability_id in self.fail_ids:
            raise RuntimeError(f"boom {capability_id}")
        return {"id": capability_id, "params": params}


class FakePlanner(CapabilityPlannerPort):
    def __init__(self, plan: CapabilityPlan) -> None:
        self._plan = plan

    async def plan(self, question, intent_type, skill, capabilities) -> CapabilityPlan:
        return self._plan


class StubReportGenerator(ReportGeneratorPort):
    """Returns a schema-valid business_report that encodes the context pack it received."""

    async def generate(self, context_pack, skill, feedback=None) -> dict[str, Any]:
        return {
            "resumen": f"sources={sorted(context_pack.available_data.keys())}",
            "hallazgos": "h",
            "recomendaciones": "r",
            "limitations": f"completeness={context_pack.data_quality.completeness}",
        }


class StubUiGenerator(UiGeneratorPort):
    """Returns a minimal valid UiSchema; avoids hitting the real LLM in tests."""

    async def generate(
        self, question, intent_type, skill, context_pack, validated_report
    ) -> dict[str, Any]:
        return {
            "layout": "executive_dashboard",
            "components": [
                {"id": "c1", "type": "metric_card", "title": "Total", "value": 1}
            ],
        }


def _set_gateway(fail_ids: set[str] | None = None) -> None:
    app.dependency_overrides[get_capability_gateway] = lambda: FakeGateway(fail_ids)


def _set_planner(plan: CapabilityPlan) -> None:
    app.dependency_overrides[get_capability_planner] = lambda: FakePlanner(plan)


def _set_report_generator(generator: ReportGeneratorPort) -> None:
    app.dependency_overrides[get_report_generator] = lambda: generator


def _set_ui_generator(generator: UiGeneratorPort) -> None:
    app.dependency_overrides[get_ui_generator] = lambda: generator


def _plan_get_sales(**params: Any) -> CapabilityPlan:
    return CapabilityPlan(
        items=[CapabilityPlanItem(capability_id="get_sales", reason="r", params=params)]
    )


@pytest.fixture(autouse=True)
def _override_dependencies():
    _set_gateway()
    _set_planner(CapabilityPlan(items=[]))
    _set_report_generator(StubReportGenerator())
    _set_ui_generator(StubUiGenerator())
    yield
    app.dependency_overrides.clear()


def test_valid_intent_runs_full_pipeline():
    _set_planner(_plan_get_sales(month=4))
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "¿Cómo van las ventas?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["resumen"] == "sources=['get_sales']"
    assert body["report"]["limitations"] == "completeness=1.0"
    assert set(body["report"].keys()) == {"resumen", "hallazgos", "recomendaciones", "limitations"}
    assert body["data_quality"]["succeeded"] == 1
    assert body["warnings"] == []
    assert body["ui"]["layout"] == "executive_dashboard"
    assert body["ui"]["components"][0]["type"] == "metric_card"


def test_partial_execution_failure_excluded_from_report():
    _set_gateway(fail_ids={"get_sales"})
    _set_planner(_plan_get_sales())
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "ventas"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["resumen"] == "sources=[]"
    assert body["data_quality"]["failed"] == 1
    assert any("failed" in w for w in body["warnings"])


def test_hallucinated_capability_is_dropped():
    _set_planner(
        CapabilityPlan(
            items=[
                CapabilityPlanItem(capability_id="get_sales", reason="ok", params={}),
                CapabilityPlanItem(
                    capability_id="get_fake_endpoint", reason="hallucinated", params={}
                ),
            ]
        )
    )
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "ventas"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["resumen"] == "sources=['get_sales']"
    assert any("get_fake_endpoint" in w for w in body["warnings"])


def test_invalid_report_is_repaired():
    class RepairOnceGenerator(ReportGeneratorPort):
        def __init__(self) -> None:
            self.calls = 0

        async def generate(self, context_pack, skill, feedback=None) -> dict[str, Any]:
            self.calls += 1
            if self.calls == 1:
                return {"resumen": "incomplete"}  # missing required keys
            return {
                "resumen": "r",
                "hallazgos": "h",
                "recomendaciones": "rec",
                "limitations": "",
            }

    _set_report_generator(RepairOnceGenerator())
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "ventas"},
    )
    assert resp.status_code == 200
    assert resp.json()["report"]["hallazgos"] == "h"


def test_unrepairable_report_returns_422():
    class AlwaysInvalidGenerator(ReportGeneratorPort):
        async def generate(self, context_pack, skill, feedback=None) -> dict[str, Any]:
            return {"resumen": "only"}

    _set_report_generator(AlwaysInvalidGenerator())
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "ventas"},
    )
    assert resp.status_code == 422


def test_marketing_plan_intent_end_to_end():
    class MarketingReportGenerator(ReportGeneratorPort):
        async def generate(self, context_pack, skill, feedback=None) -> dict[str, Any]:
            return {
                "objetivos": "o",
                "segmentos": "s",
                "acciones": "a",
                "metricas": "m",
                "limitations": "",
            }

    _set_planner(_plan_get_sales())
    _set_report_generator(MarketingReportGenerator())
    resp = client.post(
        "/business-chat",
        json={"intent_type": "marketing_plan", "question": "plan de marketing Q3"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intent_type"] == "marketing_plan"
    assert set(body["report"].keys()) == {
        "objetivos",
        "segmentos",
        "acciones",
        "metricas",
        "limitations",
    }


def test_marketing_plan_has_null_ui():
    class MarketingReportGenerator(ReportGeneratorPort):
        async def generate(self, context_pack, skill, feedback=None) -> dict[str, Any]:
            return {
                "objetivos": "o",
                "segmentos": "s",
                "acciones": "a",
                "metricas": "m",
                "limitations": "",
            }

    _set_planner(_plan_get_sales())
    _set_report_generator(MarketingReportGenerator())
    resp = client.post(
        "/business-chat",
        json={"intent_type": "marketing_plan", "question": "plan"},
    )
    assert resp.status_code == 200
    assert resp.json()["ui"] is None


def test_ui_generation_failure_does_not_break_report():
    class RaisingUiGenerator(UiGeneratorPort):
        async def generate(
            self, question, intent_type, skill, context_pack, validated_report
        ) -> dict[str, Any]:
            raise RuntimeError("ui exploded")

    _set_planner(_plan_get_sales())
    _set_ui_generator(RaisingUiGenerator())
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "ventas"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ui"] is None
    assert body["report"]["resumen"] == "sources=['get_sales']"
    assert any("ui generation failed" in w for w in body["warnings"])


def test_invalid_ui_schema_yields_null_ui_with_warning():
    class BadUiGenerator(UiGeneratorPort):
        async def generate(
            self, question, intent_type, skill, context_pack, validated_report
        ) -> dict[str, Any]:
            return {"components": [{"id": "x", "type": "not_a_real_component"}]}

    _set_planner(_plan_get_sales())
    _set_ui_generator(BadUiGenerator())
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "ventas"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ui"] is None
    assert any("ui generation" in w for w in body["warnings"])


def test_planning_error_returns_502():
    class RaisingPlanner(CapabilityPlannerPort):
        async def plan(self, question, intent_type, skill, capabilities) -> CapabilityPlan:
            raise PlanningError("planner exploded")

    app.dependency_overrides[get_capability_planner] = lambda: RaisingPlanner()
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": "ventas"},
    )
    assert resp.status_code == 502
    assert resp.json()["detail"]["request_id"]


def test_invalid_intent_returns_422():
    resp = client.post(
        "/business-chat",
        json={"intent_type": "not_a_real_intent", "question": "hola"},
    )
    assert resp.status_code == 422


def test_empty_question_returns_422():
    resp = client.post(
        "/business-chat",
        json={"intent_type": "business_report", "question": ""},
    )
    assert resp.status_code == 422


def test_missing_skill_returns_404(tmp_path):
    app.dependency_overrides[get_skill_repository] = lambda: YamlSkillRepository(tmp_path)
    resp = client.post(
        "/business-chat",
        json={"intent_type": "marketing_plan", "question": "plan"},
    )
    assert resp.status_code == 404
