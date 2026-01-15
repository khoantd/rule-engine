"""
API routes for Rules management (CRUD operations).

This module provides REST API endpoints for managing Rules, including:
- List all rules
- Get a rule by ID
- Create a new rule
- Update an existing rule
- Delete a rule
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    RuleCreateRequest,
    RuleUpdateRequest,
    RuleResponse,
    RulesListResponse,
    ErrorResponse
)
from services.rule_management import get_rule_management_service
from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from api.middleware.auth import get_api_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/rules",
    tags=["rules-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.get(
    "",
    response_model=RulesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all rules",
    description="Retrieve a list of all configured rules."
)
async def list_rules(
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RulesListResponse:
    """
    List all rules.
    
    Returns:
        List of all rules in the system
        
    Raises:
        HTTPException: If listing fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API list rules request", correlation_id=correlation_id)
    
    try:
        service = get_rule_management_service()
        rules_data = service.list_rules()
        
        # Convert to response models
        rules = [
            RuleResponse(**rule) for rule in rules_data
        ]
        
        logger.info("API list rules completed", correlation_id=correlation_id, count=len(rules))
        
        return RulesListResponse(rules=rules, count=len(rules))
        
    except ConfigurationError as e:
        logger.error("Configuration error listing rules", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error listing rules", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a rule by ID",
    description="Retrieve a specific rule by its identifier."
)
async def get_rule(
    rule_id: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleResponse:
    """
    Get a rule by ID.
    
    Args:
        rule_id: Rule identifier
        
    Returns:
        Rule details
        
    Raises:
        HTTPException: If rule not found or retrieval fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API get rule request", correlation_id=correlation_id, rule_id=rule_id)
    
    try:
        service = get_rule_management_service()
        rule_data = service.get_rule(rule_id)
        
        if not rule_data:
            logger.warning("Rule not found", correlation_id=correlation_id, rule_id=rule_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Rule with ID '{rule_id}' not found",
                    "error_code": "RULE_NOT_FOUND",
                    "context": {"rule_id": rule_id}
                }
            )
        
        logger.info("API get rule completed", correlation_id=correlation_id, rule_id=rule_id)
        
        return RuleResponse(**rule_data)
        
    except DataValidationError as e:
        logger.error("Data validation error getting rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error("Configuration error getting rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error getting rule", error=str(e), correlation_id=correlation_id, exc_info=True)
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
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new rule",
    description="Create a new rule with the provided configuration."
)
async def create_rule(
    request: RuleCreateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleResponse:
    """
    Create a new rule.
    
    Args:
        request: Rule creation request with rule data
        
    Returns:
        Created rule details
        
    Raises:
        HTTPException: If creation fails or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API create rule request", correlation_id=correlation_id, rule_id=request.id)
    
    try:
        service = get_rule_management_service()
        
        # Convert request to dict for service
        rule_data = request.dict(exclude_none=False)
        
        created_rule = service.create_rule(rule_data)
        
        logger.info("API create rule completed", correlation_id=correlation_id, rule_id=request.id)
        
        return RuleResponse(**created_rule)
        
    except DataValidationError as e:
        logger.error("Data validation error creating rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error creating rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error creating rule", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.put(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing rule",
    description="Update an existing rule with new configuration."
)
async def update_rule(
    rule_id: str,
    request: RuleUpdateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> RuleResponse:
    """
    Update an existing rule.
    
    Args:
        rule_id: Rule identifier
        request: Rule update request with updated data
        
    Returns:
        Updated rule details
        
    Raises:
        HTTPException: If update fails, rule not found, or validation fails
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API update rule request", correlation_id=correlation_id, rule_id=rule_id)
    
    try:
        service = get_rule_management_service()
        
        # Get existing rule to merge with updates
        existing_rule = service.get_rule(rule_id)
        if not existing_rule:
            logger.warning("Rule not found for update", correlation_id=correlation_id, rule_id=rule_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Rule with ID '{rule_id}' not found",
                    "error_code": "RULE_NOT_FOUND",
                    "context": {"rule_id": rule_id}
                }
            )
        
        # Merge existing data with updates (only non-None fields from request)
        rule_data = existing_rule.copy()
        update_data = request.dict(exclude_none=True)
        rule_data.update(update_data)
        
        updated_rule = service.update_rule(rule_id, rule_data)
        
        logger.info("API update rule completed", correlation_id=correlation_id, rule_id=rule_id)
        
        return RuleResponse(**updated_rule)
        
    except DataValidationError as e:
        logger.error("Data validation error updating rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error("Configuration error updating rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error updating rule", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a rule",
    description="Delete a rule by its identifier."
)
async def delete_rule(
    rule_id: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> None:
    """
    Delete a rule.
    
    Args:
        rule_id: Rule identifier
        
    Raises:
        HTTPException: If deletion fails or rule not found
    """
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info("API delete rule request", correlation_id=correlation_id, rule_id=rule_id)
    
    try:
        service = get_rule_management_service()
        service.delete_rule(rule_id)
        
        logger.info("API delete rule completed", correlation_id=correlation_id, rule_id=rule_id)
        
    except DataValidationError as e:
        logger.error("Data validation error deleting rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except ConfigurationError as e:
        logger.error("Configuration error deleting rule", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error deleting rule", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )

