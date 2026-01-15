"""
API routes for Actions/Patterns management (CRUD operations).

This module provides REST API endpoints for managing Actions (patterns), including:
- List all actions
- Get an action by pattern
- Create a new action
- Update an existing action
- Delete an action
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    ActionCreateRequest,
    ActionUpdateRequest,
    ActionResponse,
    ActionsListResponse,
    ErrorResponse
)
from services.actions_management import get_actions_management_service
from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from api.middleware.auth import get_api_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/actions",
    tags=["actions-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.get(
    "",
    response_model=ActionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all actions",
    description="Retrieve a list of all configured actions/patterns."
)
async def list_actions(
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ActionsListResponse:
    """
    List all actions/patterns.
    
    Returns:
        Dictionary of all actions (patterns mapped to messages)
        
    Raises:
        HTTPException: If listing fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API list actions request", correlation_id=correlation_id)
    
    try:
        service = get_actions_management_service()
        actions_data = service.list_actions()
        
        logger.info("API list actions completed", correlation_id=correlation_id, count=len(actions_data))
        
        return ActionsListResponse(actions=actions_data, count=len(actions_data))
        
    except ConfigurationError as e:
        logger.error("Configuration error listing actions", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error listing actions", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.get(
    "/{pattern}",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an action by pattern",
    description="Retrieve a specific action by its pattern string."
)
async def get_action(
    pattern: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ActionResponse:
    """
    Get an action by pattern.
    
    Args:
        pattern: Pattern string (e.g., "YYY", "Y--")
        
    Returns:
        Action details
        
    Raises:
        HTTPException: If action not found or retrieval fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API get action request", correlation_id=correlation_id, pattern=pattern)
    
    try:
        service = get_actions_management_service()
        message = service.get_action(pattern)
        
        if not message:
            logger.warning("Action not found", correlation_id=correlation_id, pattern=pattern)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Action with pattern '{pattern}' not found",
                    "error_code": "ACTION_NOT_FOUND",
                    "context": {"pattern": pattern}
                }
            )
        
        logger.info("API get action completed", correlation_id=correlation_id, pattern=pattern)
        
        return ActionResponse(pattern=pattern, message=message)
        
    except DataValidationError as e:
        logger.error("Data validation error getting action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error("Configuration error getting action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error getting action", error=str(e), correlation_id=correlation_id, exc_info=True)
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
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new action",
    description="Create a new action/pattern with the provided configuration."
)
async def create_action(
    request: ActionCreateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ActionResponse:
    """
    Create a new action/pattern.
    
    Args:
        request: Action creation request with pattern and message
        
    Returns:
        Created action details
        
    Raises:
        HTTPException: If creation fails or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API create action request", correlation_id=correlation_id, pattern=request.pattern)
    
    try:
        service = get_actions_management_service()
        
        created_action = service.create_action(request.pattern, request.message)
        
        # Extract pattern and message from result
        pattern = list(created_action.keys())[0]
        message = created_action[pattern]
        
        logger.info("API create action completed", correlation_id=correlation_id, pattern=pattern)
        
        return ActionResponse(pattern=pattern, message=message)
        
    except DataValidationError as e:
        logger.error("Data validation error creating action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error creating action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error creating action", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.put(
    "/{pattern}",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing action",
    description="Update an existing action/pattern with a new message."
)
async def update_action(
    pattern: str,
    request: ActionUpdateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> ActionResponse:
    """
    Update an existing action/pattern.
    
    Args:
        pattern: Pattern string
        request: Action update request with updated message
        
    Returns:
        Updated action details
        
    Raises:
        HTTPException: If update fails, action not found, or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API update action request", correlation_id=correlation_id, pattern=pattern)
    
    try:
        service = get_actions_management_service()
        
        updated_action = service.update_action(pattern, request.message)
        
        # Extract pattern and message from result
        pattern_key = list(updated_action.keys())[0]
        message = updated_action[pattern_key]
        
        logger.info("API update action completed", correlation_id=correlation_id, pattern=pattern)
        
        return ActionResponse(pattern=pattern_key, message=message)
        
    except DataValidationError as e:
        logger.error("Data validation error updating action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error updating action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error updating action", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.delete(
    "/{pattern}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an action",
    description="Delete an action/pattern by its pattern string."
)
async def delete_action(
    pattern: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> None:
    """
    Delete an action/pattern.
    
    Args:
        pattern: Pattern string
        
    Raises:
        HTTPException: If deletion fails or action not found
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API delete action request", correlation_id=correlation_id, pattern=pattern)
    
    try:
        service = get_actions_management_service()
        service.delete_action(pattern)
        
        logger.info("API delete action completed", correlation_id=correlation_id, pattern=pattern)
        
    except DataValidationError as e:
        logger.error("Data validation error deleting action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error deleting action", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error deleting action", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )

