from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapabilityPlanItem:
    """One step of the planner's output: which capability to call and why."""

    capability_id: str
    reason: str
    params: dict[str, Any] = field(default_factory=dict)
