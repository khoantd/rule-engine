"""
API routes for RuleSets management (CRUD operations).

This module provides REST API endpoints for managing RuleSets, including:
- List all rulesets
- Get a ruleset by name
- Create a new ruleset
- Update an existing ruleset
- Delete a ruleset

Note: RuleSets are logical groupings of rules and actions. The actual
persistence is managed through rules and actions management.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    RuleSetCreateRequest,
    RuleSetUpdateRequest,
    RuleSetResponse,
    RuleSetsListResponse,
    ErrorResponse
)
from services.ruleset_management import get_ruleset_management_service
from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from api.middleware.auth import get_api_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/rulesets",
    tags=["rulesets-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.get(
    "",
    response_model=RuleSetsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all rulesets",
    description="Retrieve a list of all configured rulesets."
)
async def list_rulesets(
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleSetsListResponse:
    """
    List all rulesets.
    
    Returns:
        List of all rulesets in the system
        
    Raises:
        HTTPException: If listing fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API list rulesets request", correlation_id=correlation_id)
    
    try:
        service = get_ruleset_management_service()
        rulesets_data = service.list_rulesets()
        
        # Convert to response models
        rulesets = [
            RuleSetResponse(**ruleset) for ruleset in rulesets_data
        ]
        
        logger.info("API list rulesets completed", correlation_id=correlation_id, count=len(rulesets))
        
        return RuleSetsListResponse(rulesets=rulesets, count=len(rulesets))
        
    except ConfigurationError as e:
        logger.error("Configuration error listing rulesets", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error listing rulesets", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.get(
    "/{ruleset_name}",
    response_model=RuleSetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a ruleset by name",
    description="Retrieve a specific ruleset by its name."
)
async def get_ruleset(
    ruleset_name: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleSetResponse:
    """
    Get a ruleset by name.
    
    Args:
        ruleset_name: RuleSet name
        
    Returns:
        RuleSet details
        
    Raises:
        HTTPException: If ruleset not found or retrieval fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API get ruleset request", correlation_id=correlation_id, ruleset_name=ruleset_name)
    
    try:
        service = get_ruleset_management_service()
        ruleset_data = service.get_ruleset(ruleset_name)
        
        if not ruleset_data:
            logger.warning("RuleSet not found", correlation_id=correlation_id, ruleset_name=ruleset_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"RuleSet with name '{ruleset_name}' not found",
                    "error_code": "RULESET_NOT_FOUND",
                    "context": {"ruleset_name": ruleset_name}
                }
            )
        
        logger.info("API get ruleset completed", correlation_id=correlation_id, ruleset_name=ruleset_name)
        
        return RuleSetResponse(**ruleset_data)
        
    except DataValidationError as e:
        logger.error("Data validation error getting ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error("Configuration error getting ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error getting ruleset", error=str(e), correlation_id=correlation_id, exc_info=True)
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
    response_model=RuleSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ruleset",
    description="Create a new ruleset with the provided configuration. Note: RuleSets are logical groupings and validation only."
)
async def create_ruleset(
    request: RuleSetCreateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleSetResponse:
    """
    Create a new ruleset.
    
    This operation validates the ruleset configuration but does not persist
    it directly. RuleSets are logical groupings of rules and actions.
    
    Args:
        request: RuleSet creation request with ruleset data
        
    Returns:
        Created ruleset details
        
    Raises:
        HTTPException: If creation fails or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API create ruleset request", correlation_id=correlation_id, ruleset_name=request.ruleset_name)
    
    try:
        service = get_ruleset_management_service()
        
        # Convert request to dict for service
        ruleset_data = request.dict(exclude_none=False)
        
        created_ruleset = service.create_ruleset(ruleset_data)
        
        logger.info("API create ruleset completed", correlation_id=correlation_id, ruleset_name=request.ruleset_name)
        
        return RuleSetResponse(**created_ruleset)
        
    except DataValidationError as e:
        logger.error("Data validation error creating ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error creating ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error creating ruleset", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.put(
    "/{ruleset_name}",
    response_model=RuleSetResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing ruleset",
    description="Update an existing ruleset with new configuration. Note: RuleSets are logical groupings and validation only."
)
async def update_ruleset(
    ruleset_name: str,
    request: RuleSetUpdateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleSetResponse:
    """
    Update an existing ruleset.
    
    This operation validates the ruleset configuration but does not persist
    it directly. RuleSets are logical groupings of rules and actions.
    
    Args:
        ruleset_name: RuleSet name
        request: RuleSet update request with updated data
        
    Returns:
        Updated ruleset details
        
    Raises:
        HTTPException: If update fails, ruleset not found, or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API update ruleset request", correlation_id=correlation_id, ruleset_name=ruleset_name)
    
    try:
        service = get_ruleset_management_service()
        
        # Get existing ruleset to merge with updates
        existing_ruleset = service.get_ruleset(ruleset_name)
        if not existing_ruleset:
            logger.warning("RuleSet not found for update", correlation_id=correlation_id, ruleset_name=ruleset_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"RuleSet with name '{ruleset_name}' not found",
                    "error_code": "RULESET_NOT_FOUND",
                    "context": {"ruleset_name": ruleset_name}
                }
            )
        
        # Merge existing data with updates (only non-None fields from request)
        ruleset_data = existing_ruleset.copy()
        update_data = request.dict(exclude_none=True)
        ruleset_data.update(update_data)
        
        updated_ruleset = service.update_ruleset(ruleset_name, ruleset_data)
        
        logger.info("API update ruleset completed", correlation_id=correlation_id, ruleset_name=ruleset_name)
        
        return RuleSetResponse(**updated_ruleset)
        
    except DataValidationError as e:
        logger.error("Data validation error updating ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error("Configuration error updating ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error updating ruleset", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.delete(
    "/{ruleset_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ruleset",
    description="Delete a ruleset by its name. Note: This is a logical operation that validates the deletion."
)
async def delete_ruleset(
    ruleset_name: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> None:
    """
    Delete a ruleset.
    
    This operation validates the deletion but does not remove the underlying
    rules and actions, as RuleSets are logical groupings.
    
    Args:
        ruleset_name: RuleSet name
        
    Raises:
        HTTPException: If deletion fails or ruleset not found
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API delete ruleset request", correlation_id=correlation_id, ruleset_name=ruleset_name)
    
    try:
        service = get_ruleset_management_service()
        service.delete_ruleset(ruleset_name)
        
        logger.info("API delete ruleset completed", correlation_id=correlation_id, ruleset_name=ruleset_name)
        
    except DataValidationError as e:
        logger.error("Data validation error deleting ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error deleting ruleset", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error deleting ruleset", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )

