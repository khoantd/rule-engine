"""
API routes for Conditions management (CRUD operations).

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from api.deps import get_conditions_management_service_dep, get_correlation_id
from api.middleware.auth import get_api_key
from api.models import (
    ConditionCreateRequest,
    ConditionResponse,
    ConditionsListResponse,
    ConditionUpdateRequest,
    ErrorResponse,
)
from common.exceptions import NotFoundError
from common.logger import get_logger
from services.conditions_management import ConditionsManagementService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/conditions",
    tags=["conditions-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.get(
    "",
    response_model=ConditionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all conditions",
    description="Retrieve a list of all configured conditions.",
)
async def list_conditions(
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ConditionsManagementService = Depends(get_conditions_management_service_dep),
) -> ConditionsListResponse:
    """List all conditions."""
    logger.info("API list conditions request", correlation_id=correlation_id)
    conditions_data = service.list_conditions()
    conditions = [ConditionResponse(**condition) for condition in conditions_data]
    logger.info(
        "API list conditions completed", correlation_id=correlation_id, count=len(conditions)
    )
    return ConditionsListResponse(conditions=conditions, count=len(conditions))


@router.get(
    "/{condition_id}",
    response_model=ConditionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a condition by ID",
    description="Retrieve a specific condition by its identifier.",
)
async def get_condition(
    condition_id: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ConditionsManagementService = Depends(get_conditions_management_service_dep),
) -> ConditionResponse:
    """Get a condition by ID."""
    logger.info(
        "API get condition request", correlation_id=correlation_id, condition_id=condition_id
    )
    condition_data = service.get_condition(condition_id)
    if not condition_data:
        logger.warning(
            "Condition not found", correlation_id=correlation_id, condition_id=condition_id
        )
        raise NotFoundError(
            f"Condition with ID '{condition_id}' not found",
            error_code="CONDITION_NOT_FOUND",
            context={"condition_id": condition_id},
        )
    logger.info(
        "API get condition completed", correlation_id=correlation_id, condition_id=condition_id
    )
    return ConditionResponse(**condition_data)


@router.post(
    "",
    response_model=ConditionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new condition",
    description="Create a new condition with the provided configuration.",
)
async def create_condition(
    request: ConditionCreateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ConditionsManagementService = Depends(get_conditions_management_service_dep),
) -> ConditionResponse:
    """Create a new condition."""
    logger.info(
        "API create condition request",
        correlation_id=correlation_id,
        condition_id=request.condition_id,
    )
    condition_data = request.model_dump(exclude_none=False)
    created_condition = service.create_condition(condition_data)
    logger.info(
        "API create condition completed",
        correlation_id=correlation_id,
        condition_id=request.condition_id,
    )
    return ConditionResponse(**created_condition)


@router.put(
    "/{condition_id}",
    response_model=ConditionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing condition",
    description="Update an existing condition with new configuration.",
)
async def update_condition(
    condition_id: str,
    request: ConditionUpdateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ConditionsManagementService = Depends(get_conditions_management_service_dep),
) -> ConditionResponse:
    """Update an existing condition."""
    logger.info(
        "API update condition request", correlation_id=correlation_id, condition_id=condition_id
    )
    existing_condition = service.get_condition(condition_id)
    if not existing_condition:
        logger.warning(
            "Condition not found for update",
            correlation_id=correlation_id,
            condition_id=condition_id,
        )
        raise NotFoundError(
            f"Condition with ID '{condition_id}' not found",
            error_code="CONDITION_NOT_FOUND",
            context={"condition_id": condition_id},
        )
    condition_data = existing_condition.copy()
    condition_data.update(request.model_dump(exclude_none=True))
    updated_condition = service.update_condition(condition_id, condition_data)
    logger.info(
        "API update condition completed", correlation_id=correlation_id, condition_id=condition_id
    )
    return ConditionResponse(**updated_condition)


@router.delete(
    "/{condition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a condition",
    description="Delete a condition by its identifier.",
)
async def delete_condition(
    condition_id: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ConditionsManagementService = Depends(get_conditions_management_service_dep),
) -> None:
    """Delete a condition."""
    logger.info(
        "API delete condition request", correlation_id=correlation_id, condition_id=condition_id
    )
    service.delete_condition(condition_id)
    logger.info(
        "API delete condition completed", correlation_id=correlation_id, condition_id=condition_id
    )
