"""
API routes for Conditions management (CRUD operations).

This module provides REST API endpoints for managing Conditions, including:
- List all conditions
- Get a condition by ID
- Create a new condition
- Update an existing condition
- Delete a condition
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    ConditionCreateRequest,
    ConditionUpdateRequest,
    ConditionResponse,
    ConditionsListResponse,
    ErrorResponse
)
from services.conditions_management import get_conditions_management_service
from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from api.middleware.auth import get_api_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/conditions",
    tags=["conditions-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.get(
    "",
    response_model=ConditionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all conditions",
    description="Retrieve a list of all configured conditions."
)
async def list_conditions(
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ConditionsListResponse:
    """
    List all conditions.
    
    Returns:
        List of all conditions in the system
        
    Raises:
        HTTPException: If listing fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API list conditions request", correlation_id=correlation_id)
    
    try:
        service = get_conditions_management_service()
        conditions_data = service.list_conditions()
        
        # Convert to response models
        conditions = [
            ConditionResponse(**condition) for condition in conditions_data
        ]
        
        logger.info("API list conditions completed", correlation_id=correlation_id, count=len(conditions))
        
        return ConditionsListResponse(conditions=conditions, count=len(conditions))
        
    except ConfigurationError as e:
        logger.error("Configuration error listing conditions", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error listing conditions", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.get(
    "/{condition_id}",
    response_model=ConditionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a condition by ID",
    description="Retrieve a specific condition by its identifier."
)
async def get_condition(
    condition_id: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ConditionResponse:
    """
    Get a condition by ID.
    
    Args:
        condition_id: Condition identifier
        
    Returns:
        Condition details
        
    Raises:
        HTTPException: If condition not found or retrieval fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API get condition request", correlation_id=correlation_id, condition_id=condition_id)
    
    try:
        service = get_conditions_management_service()
        condition_data = service.get_condition(condition_id)
        
        if not condition_data:
            logger.warning("Condition not found", correlation_id=correlation_id, condition_id=condition_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Condition with ID '{condition_id}' not found",
                    "error_code": "CONDITION_NOT_FOUND",
                    "context": {"condition_id": condition_id}
                }
            )
        
        logger.info("API get condition completed", correlation_id=correlation_id, condition_id=condition_id)
        
        return ConditionResponse(**condition_data)
        
    except DataValidationError as e:
        logger.error("Data validation error getting condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error("Configuration error getting condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error getting condition", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.post(
    "",
    response_model=ConditionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new condition",
    description="Create a new condition with the provided configuration."
)
async def create_condition(
    request: ConditionCreateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ConditionResponse:
    """
    Create a new condition.
    
    Args:
        request: Condition creation request with condition data
        
    Returns:
        Created condition details
        
    Raises:
        HTTPException: If creation fails or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API create condition request", correlation_id=correlation_id, condition_id=request.condition_id)
    
    try:
        service = get_conditions_management_service()
        
        # Convert request to dict for service
        condition_data = request.dict(exclude_none=False)
        
        created_condition = service.create_condition(condition_data)
        
        logger.info("API create condition completed", correlation_id=correlation_id, condition_id=request.condition_id)
        
        return ConditionResponse(**created_condition)
        
    except DataValidationError as e:
        logger.error("Data validation error creating condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error creating condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error creating condition", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.put(
    "/{condition_id}",
    response_model=ConditionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing condition",
    description="Update an existing condition with new configuration."
)
async def update_condition(
    condition_id: str,
    request: ConditionUpdateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ConditionResponse:
    """
    Update an existing condition.
    
    Args:
        condition_id: Condition identifier
        request: Condition update request with updated data
        
    Returns:
        Updated condition details
        
    Raises:
        HTTPException: If update fails, condition not found, or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API update condition request", correlation_id=correlation_id, condition_id=condition_id)
    
    try:
        service = get_conditions_management_service()
        
        # Get existing condition to merge with updates
        existing_condition = service.get_condition(condition_id)
        if not existing_condition:
            logger.warning("Condition not found for update", correlation_id=correlation_id, condition_id=condition_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Condition with ID '{condition_id}' not found",
                    "error_code": "CONDITION_NOT_FOUND",
                    "context": {"condition_id": condition_id}
                }
            )
        
        # Merge existing data with updates (only non-None fields from request)
        condition_data = existing_condition.copy()
        update_data = request.dict(exclude_none=True)
        condition_data.update(update_data)
        
        updated_condition = service.update_condition(condition_id, condition_data)
        
        logger.info("API update condition completed", correlation_id=correlation_id, condition_id=condition_id)
        
        return ConditionResponse(**updated_condition)
        
    except DataValidationError as e:
        logger.error("Data validation error updating condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error("Configuration error updating condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error updating condition", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.delete(
    "/{condition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a condition",
    description="Delete a condition by its identifier."
)
async def delete_condition(
    condition_id: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> None:
    """
    Delete a condition.
    
    Args:
        condition_id: Condition identifier
        
    Raises:
        HTTPException: If deletion fails or condition not found
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API delete condition request", correlation_id=correlation_id, condition_id=condition_id)
    
    try:
        service = get_conditions_management_service()
        service.delete_condition(condition_id)
        
        logger.info("API delete condition completed", correlation_id=correlation_id, condition_id=condition_id)
        
    except DataValidationError as e:
        logger.error("Data validation error deleting condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error deleting condition", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error deleting condition", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )

