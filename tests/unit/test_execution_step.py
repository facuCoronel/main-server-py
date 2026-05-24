from typing import Any

from src.application.dtos.pipeline import CapabilityPlan, DataQuality, ExecutionResult
from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.application.pipeline.execution_step import run_execution
from src.domain.value_objects.capability import CapabilityDescriptor, ExecutionStatus
from src.domain.value_objects.capability_plan import CapabilityPlanItem


class FakeGateway(CapabilityGatewayPort):
    def __init__(self, fail_ids: set[str] | None = None) -> None:
        self.fail_ids = fail_ids or set()
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def discover(self) -> list[CapabilityDescriptor]:
        return []

    async def execute(self, capability_id: str, params: dict[str, Any]) -> Any:
        self.calls.append((capability_id, params))
        if capability_id in self.fail_ids:
            raise RuntimeError(f"boom {capability_id}")
        return {"id": capability_id, "params": params}


def _plan(*ids: str) -> CapabilityPlan:
    return CapabilityPlan(
        items=[CapabilityPlanItem(capability_id=i, reason="r", params={}) for i in ids]
    )


async def test_all_success():
    results = await run_execution(FakeGateway(), _plan("a", "b"))
    assert [r.status for r in results] == [ExecutionStatus.SUCCESS, ExecutionStatus.SUCCESS]
    assert results[0].data == {"id": "a", "params": {}}


async def test_partial_failure_is_tolerated():
    gw = FakeGateway(fail_ids={"b"})
    results = await run_execution(gw, _plan("a", "b", "c"))

    statuses = {r.capability_id: r.status for r in results}
    assert statuses == {
        "a": ExecutionStatus.SUCCESS,
        "b": ExecutionStatus.FAILED,
        "c": ExecutionStatus.SUCCESS,
    }
    failed = next(r for r in results if r.capability_id == "b")
    assert failed.error is not None and "boom b" in failed.error
    # 'c' still executed after 'b' failed
    assert ("c", {}) in gw.calls


async def test_empty_plan_yields_no_results():
    results = await run_execution(FakeGateway(), CapabilityPlan(items=[]))
    assert results == []


def test_data_quality_from_results():
    results = [
        ExecutionResult(capability_id="a", status=ExecutionStatus.SUCCESS, data={}),
        ExecutionResult(capability_id="b", status=ExecutionStatus.FAILED, error="x"),
    ]
    dq = DataQuality.from_results(results)
    assert dq.requested == 2
    assert dq.succeeded == 1
    assert dq.failed == 1
    assert dq.completeness == 0.5
    assert dq.failed_capabilities == ["b"]
