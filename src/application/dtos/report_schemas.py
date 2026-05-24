from pydantic import BaseModel

from src.domain.value_objects.intent_type import IntentType


class BusinessReportOutput(BaseModel):
    resumen: str
    hallazgos: str
    recomendaciones: str
    limitations: str = ""


class MarketingPlanOutput(BaseModel):
    objetivos: str
    segmentos: str
    acciones: str
    metricas: str
    limitations: str = ""


# Maps a skill's `output_schema` value to the Pydantic model that validates the final report.
OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    IntentType.BUSINESS_REPORT.value: BusinessReportOutput,
    IntentType.MARKETING_PLAN.value: MarketingPlanOutput,
}
