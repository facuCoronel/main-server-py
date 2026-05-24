from typing import Any

from pydantic import BaseModel, Field

from src.application.dtos.pipeline import DataQuality
from src.domain.value_objects.intent_type import IntentType


class BusinessChatRequest(BaseModel):
    intent_type: IntentType
    question: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class BusinessChatResponse(BaseModel):
    request_id: str
    intent_type: IntentType
    report: dict[str, Any] = Field(default_factory=dict)
    data_quality: DataQuality = Field(default_factory=DataQuality)
    warnings: list[str] = Field(default_factory=list)
