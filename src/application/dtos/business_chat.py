from typing import Any

from pydantic import BaseModel, Field

from src.application.dtos.pipeline import DataQuality
from src.domain.value_objects.intent_type import IntentType


class BusinessChatCommand(BaseModel):
    """Input to RunBusinessChatUseCase (crosses the use-case boundary)."""

    request_id: str
    intent_type: IntentType
    question: str
    params: dict[str, Any] = Field(default_factory=dict)


class BusinessChatResult(BaseModel):
    """Output of RunBusinessChatUseCase."""

    request_id: str
    intent_type: IntentType
    report: dict[str, Any] = Field(default_factory=dict)
    ui: dict[str, Any] | None = None
    data_quality: DataQuality = Field(default_factory=DataQuality)
    warnings: list[str] = Field(default_factory=list)
