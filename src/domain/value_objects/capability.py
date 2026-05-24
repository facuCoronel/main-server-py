from dataclasses import dataclass, field
from enum import StrEnum


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True)
class CapabilityParam:
    name: str
    type: str = "string"
    required: bool = False
    description: str | None = None


@dataclass(frozen=True)
class CapabilityDescriptor:
    """A capability the system is allowed to execute, as discovered from the catalog.

    The planner may only select capabilities present in a discovered list of these.
    """

    id: str
    description: str
    params: list[CapabilityParam] = field(default_factory=list)

    @property
    def required_params(self) -> list[str]:
        return [p.name for p in self.params if p.required]
