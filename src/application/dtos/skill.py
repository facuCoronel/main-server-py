from pydantic import BaseModel, Field

from src.domain.value_objects.intent_type import IntentType


class PlannerConfig(BaseModel):
    system_prompt: str
    max_capabilities: int = Field(default=8, ge=1)


class ReportConfig(BaseModel):
    system_prompt: str
    sections: list[str] = Field(default_factory=list)


class SkillDefinition(BaseModel):
    """Validated representation of a local skill (parsed from YAML).

    Skills carry only prompts, limits and metadata — never real endpoints.
    """

    intent_type: IntentType
    display_name: str
    description: str
    language: str = "es"
    planner: PlannerConfig
    report: ReportConfig
    output_schema: str
    constraints: list[str] = Field(default_factory=list)
