import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_run_business_chat_use_case
from src.api.schemas.business_chat import BusinessChatRequest, BusinessChatResponse
from src.application.dtos.business_chat import BusinessChatCommand
from src.application.errors import (
    ApplicationError,
    OutputValidationError,
    PlanningError,
    SkillNotFound,
)
from src.application.use_cases.run_business_chat import RunBusinessChatUseCase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["business-chat"])


def _error(request_id: str, exc: Exception) -> dict[str, str]:
    return {"error": str(exc), "request_id": request_id}


@router.post("/business-chat", response_model=BusinessChatResponse)
async def business_chat(
    request: BusinessChatRequest,
    use_case: RunBusinessChatUseCase = Depends(get_run_business_chat_use_case),
) -> BusinessChatResponse:
    command = BusinessChatCommand(
        request_id=str(uuid4()),
        intent_type=request.intent_type,
        question=request.question,
        params=request.params,
    )

    try:
        result = await use_case.execute(command)
    except SkillNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_error(command.request_id, exc)
        ) from exc
    except OutputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error(command.request_id, exc),
        ) from exc
    except PlanningError as exc:
        # The LLM planner failed to produce a usable plan — treat as an upstream failure.
        logger.warning("[%s] planning failed: %s", command.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=_error(command.request_id, exc)
        ) from exc
    except ApplicationError as exc:
        logger.exception("[%s] application error", command.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error(command.request_id, exc),
        ) from exc
    except Exception as exc:
        # Unexpected failure in an upstream dependency (catalog/LLM/HTTP). Log full trace,
        # return a clean controlled response with the correlation id.
        logger.exception("[%s] unexpected pipeline error", command.request_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=_error(command.request_id, exc)
        ) from exc

    logger.info("[%s] business-chat done (%d warnings)", command.request_id, len(result.warnings))
    return BusinessChatResponse(**result.model_dump())
