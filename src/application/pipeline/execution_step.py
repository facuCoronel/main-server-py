import logging

from src.application.dtos.pipeline import CapabilityPlan, ExecutionResult
from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.domain.value_objects.capability import ExecutionStatus

logger = logging.getLogger(__name__)


async def run_execution(
    gateway: CapabilityGatewayPort, plan: CapabilityPlan
) -> list[ExecutionResult]:
    """Execute each planned capability, tolerating partial failures.

    A failing capability is recorded as FAILED and does not abort the remaining ones.
    """
    results: list[ExecutionResult] = []
    for item in plan.items:
        try:
            data = await gateway.execute(item.capability_id, item.params)
            results.append(
                ExecutionResult(
                    capability_id=item.capability_id,
                    status=ExecutionStatus.SUCCESS,
                    data=data,
                )
            )
        except Exception as exc:  # partial-failure tolerance is intentional
            logger.warning("capability '%s' failed: %s", item.capability_id, exc)
            results.append(
                ExecutionResult(
                    capability_id=item.capability_id,
                    status=ExecutionStatus.FAILED,
                    error=str(exc),
                )
            )
    return results
