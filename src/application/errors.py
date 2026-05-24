class ApplicationError(Exception):
    """Base class for application-layer errors (independent of delivery mechanism)."""


class SkillNotFound(ApplicationError):
    def __init__(self, intent_type: str) -> None:
        super().__init__(f"No skill defined for intent_type '{intent_type}'.")
        self.intent_type = intent_type


class PlanningError(ApplicationError):
    """Raised when the planner cannot produce a usable plan."""


class OutputValidationError(ApplicationError):
    """Raised when the final report cannot be validated even after repair."""
