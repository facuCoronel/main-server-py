from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_COMPONENT_TYPES = {
    "metric_card",
    "bar_chart",
    "line_chart",
    "pie_chart",
    "table",
    "insight_card",
    "warning_card",
    "recommendation_list",
}


class UiComponent(BaseModel):
    """A single declarative UI component.

    Lenient on purpose: only `id` and a known `type` are required; any extra
    per-type fields (value, format, source, xField, yField, data, columns,
    items, ...) are accepted as-is so the frontend can interpret them.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    title: str | None = None

    @field_validator("type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in ALLOWED_COMPONENT_TYPES:
            raise ValueError(
                f"unknown component type '{v}'; allowed: {sorted(ALLOWED_COMPONENT_TYPES)}"
            )
        return v


class UiSchema(BaseModel):
    """Declarative UI produced after the report is validated.

    Backend-agnostic: the frontend transforms this into EChartsOption.
    """

    model_config = ConfigDict(extra="allow")

    layout: str = "executive_dashboard"
    components: list[UiComponent] = Field(default_factory=list)
