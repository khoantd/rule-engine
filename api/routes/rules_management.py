"""
API routes for Rules management (CRUD operations).

This module provides REST API endpoints for managing Rules, including:
- List all rules
- Get a rule by ID
- Create a new rule
- Update an existing rule
- Delete a rule

Domain exceptions propagate to the global API exception handler
(``api.middleware.errors``).
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from api.deps import get_correlation_id, get_rule_management_service_dep
from api.middleware.auth import get_api_key
from api.models import (
    ErrorResponse,
    RuleCreateRequest,
    RuleResponse,
    RulesListResponse,
    RuleUpdateRequest,
)
from common.exceptions import NotFoundError
from common.logger import get_logger
from services.rule_management import RuleManagementService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/rules",
    tags=["rules-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.get(
    "",
    response_model=RulesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all rules",
    description="Retrieve a list of all configured rules.",
)
async def list_rules(
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleManagementService = Depends(get_rule_management_service_dep),
) -> RulesListResponse:
    """List all rules."""
    logger.info("API list rules request", correlation_id=correlation_id)
    rules_data = service.list_rules()
    rules = [RuleResponse(**rule) for rule in rules_data]
    logger.info("API list rules completed", correlation_id=correlation_id, count=len(rules))
    return RulesListResponse(rules=rules, count=len(rules))


@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a rule by ID",
    description="Retrieve a specific rule by its identifier.",
)
async def get_rule(
    rule_id: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleManagementService = Depends(get_rule_management_service_dep),
) -> RuleResponse:
    """Get a rule by ID."""
    logger.info("API get rule request", correlation_id=correlation_id, rule_id=rule_id)
    rule_data = service.get_rule(rule_id)
    if not rule_data:
        logger.warning("Rule not found", correlation_id=correlation_id, rule_id=rule_id)
        raise NotFoundError(
            f"Rule with ID '{rule_id}' not found",
            error_code="RULE_NOT_FOUND",
            context={"rule_id": rule_id},
        )
    logger.info("API get rule completed", correlation_id=correlation_id, rule_id=rule_id)
    return RuleResponse(**rule_data)


@router.post(
    "",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new rule",
    description="Create a new rule with the provided configuration.",
)
async def create_rule(
    request: RuleCreateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleManagementService = Depends(get_rule_management_service_dep),
) -> RuleResponse:
    """Create a new rule."""
    logger.info("API create rule request", correlation_id=correlation_id, rule_id=request.id)
    rule_data = request.model_dump(exclude_none=False)
    created_rule = service.create_rule(rule_data)
    logger.info("API create rule completed", correlation_id=correlation_id, rule_id=request.id)
    return RuleResponse(**created_rule)


@router.put(
    "/{rule_id}",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing rule",
    description="Update an existing rule with new configuration.",
)
async def update_rule(
    rule_id: str,
    request: RuleUpdateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleManagementService = Depends(get_rule_management_service_dep),
) -> RuleResponse:
    """Update an existing rule."""
    logger.info("API update rule request", correlation_id=correlation_id, rule_id=rule_id)
    existing_rule = service.get_rule(rule_id)
    if not existing_rule:
        logger.warning("Rule not found for update", correlation_id=correlation_id, rule_id=rule_id)
        raise NotFoundError(
            f"Rule with ID '{rule_id}' not found",
            error_code="RULE_NOT_FOUND",
            context={"rule_id": rule_id},
        )
    rule_data = existing_rule.copy()
    update_data = request.model_dump(exclude_none=True)
    rule_data.update(update_data)
    # Only one of result/action_result may be sent; drop the stale alias from the
    # merged dict so update_rule does not overwrite the client's field.
    if "result" in update_data and "action_result" not in update_data:
        rule_data.pop("action_result", None)
    elif "action_result" in update_data and "result" not in update_data:
        rule_data.pop("result", None)
    updated_rule = service.update_rule(rule_id, rule_data)
    logger.info("API update rule completed", correlation_id=correlation_id, rule_id=rule_id)
    return RuleResponse(**updated_rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a rule",
    description="Delete a rule by its identifier.",
)
async def delete_rule(
    rule_id: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleManagementService = Depends(get_rule_management_service_dep),
) -> None:
    """Delete a rule."""
    logger.info("API delete rule request", correlation_id=correlation_id, rule_id=rule_id)
    service.delete_rule(rule_id)
    logger.info("API delete rule completed", correlation_id=correlation_id, rule_id=rule_id)
