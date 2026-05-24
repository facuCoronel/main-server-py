from typing import Any

from pydantic import BaseModel, Field

from src.domain.value_objects.capability import ExecutionStatus
from src.domain.value_objects.capability_plan import CapabilityPlanItem


class CapabilityPlan(BaseModel):
    """Structured output of the planner step (LLM)."""

    items: list[CapabilityPlanItem] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    capability_id: str
    status: ExecutionStatus
    data: Any | None = None
    error: str | None = None


class DataQuality(BaseModel):
    requested: int = 0
    succeeded: int = 0
    failed: int = 0
    completeness: float = 0.0
    failed_capabilities: list[str] = Field(default_factory=list)

    @classmethod
    def from_results(cls, results: list[ExecutionResult]) -> "DataQuality":
        requested = len(results)
        succeeded = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)
        failed = requested - succeeded
        return cls(
            requested=requested,
            succeeded=succeeded,
            failed=failed,
            completeness=(succeeded / requested) if requested else 0.0,
            failed_capabilities=[
                r.capability_id for r in results if r.status == ExecutionStatus.FAILED
            ],
        )


class ContextPack(BaseModel):
    business_context: dict[str, Any] = Field(default_factory=dict)
    available_data: dict[str, Any] = Field(default_factory=dict)
    data_quality: DataQuality = Field(default_factory=DataQuality)
