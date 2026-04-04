"""
API routes for RuleSets management (CRUD operations).

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from api.deps import get_correlation_id, get_ruleset_management_service_dep
from api.middleware.auth import get_api_key
from api.models import (
    ErrorResponse,
    RuleSetCreateRequest,
    RuleSetResponse,
    RuleSetsListResponse,
    RuleSetUpdateRequest,
)
from common.exceptions import NotFoundError
from common.logger import get_logger
from services.ruleset_management import RuleSetManagementService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/rulesets",
    tags=["rulesets-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.get(
    "",
    response_model=RuleSetsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all rulesets",
    description="Retrieve a list of all configured rulesets.",
)
async def list_rulesets(
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleSetManagementService = Depends(get_ruleset_management_service_dep),
) -> RuleSetsListResponse:
    """List all rulesets."""
    logger.info("API list rulesets request", correlation_id=correlation_id)
    rulesets_data = service.list_rulesets()
    rulesets = [RuleSetResponse(**ruleset) for ruleset in rulesets_data]
    logger.info("API list rulesets completed", correlation_id=correlation_id, count=len(rulesets))
    return RuleSetsListResponse(rulesets=rulesets, count=len(rulesets))


@router.get(
    "/{ruleset_name}",
    response_model=RuleSetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a ruleset by name",
    description="Retrieve a specific ruleset by its name.",
)
async def get_ruleset(
    ruleset_name: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleSetManagementService = Depends(get_ruleset_management_service_dep),
) -> RuleSetResponse:
    """Get a ruleset by name."""
    logger.info("API get ruleset request", correlation_id=correlation_id, ruleset_name=ruleset_name)
    ruleset_data = service.get_ruleset(ruleset_name)
    if not ruleset_data:
        logger.warning(
            "RuleSet not found", correlation_id=correlation_id, ruleset_name=ruleset_name
        )
        raise NotFoundError(
            f"RuleSet with name '{ruleset_name}' not found",
            error_code="RULESET_NOT_FOUND",
            context={"ruleset_name": ruleset_name},
        )
    logger.info(
        "API get ruleset completed", correlation_id=correlation_id, ruleset_name=ruleset_name
    )
    return RuleSetResponse(**ruleset_data)


@router.post(
    "",
    response_model=RuleSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ruleset",
    description=(
        "Create a new ruleset with the provided configuration. "
        "Note: RuleSets are logical groupings and validation only."
    ),
)
async def create_ruleset(
    request: RuleSetCreateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleSetManagementService = Depends(get_ruleset_management_service_dep),
) -> RuleSetResponse:
    """Create a new ruleset."""
    logger.info(
        "API create ruleset request",
        correlation_id=correlation_id,
        ruleset_name=request.ruleset_name,
    )
    ruleset_data = request.model_dump(exclude_none=False)
    created_ruleset = service.create_ruleset(ruleset_data)
    logger.info(
        "API create ruleset completed",
        correlation_id=correlation_id,
        ruleset_name=request.ruleset_name,
    )
    return RuleSetResponse(**created_ruleset)


@router.put(
    "/{ruleset_name}",
    response_model=RuleSetResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing ruleset",
    description=(
        "Update an existing ruleset with new configuration. "
        "Note: RuleSets are logical groupings and validation only."
    ),
)
async def update_ruleset(
    ruleset_name: str,
    request: RuleSetUpdateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleSetManagementService = Depends(get_ruleset_management_service_dep),
) -> RuleSetResponse:
    """Update an existing ruleset."""
    logger.info(
        "API update ruleset request", correlation_id=correlation_id, ruleset_name=ruleset_name
    )
    existing_ruleset = service.get_ruleset(ruleset_name)
    if not existing_ruleset:
        logger.warning(
            "RuleSet not found for update", correlation_id=correlation_id, ruleset_name=ruleset_name
        )
        raise NotFoundError(
            f"RuleSet with name '{ruleset_name}' not found",
            error_code="RULESET_NOT_FOUND",
            context={"ruleset_name": ruleset_name},
        )
    ruleset_data = existing_ruleset.copy()
    ruleset_data.update(request.model_dump(exclude_none=True))
    updated_ruleset = service.update_ruleset(ruleset_name, ruleset_data)
    logger.info(
        "API update ruleset completed", correlation_id=correlation_id, ruleset_name=ruleset_name
    )
    return RuleSetResponse(**updated_ruleset)


@router.delete(
    "/{ruleset_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ruleset",
    description=(
        "Delete a ruleset by its name. Note: This is a logical operation that validates the deletion."
    ),
)
async def delete_ruleset(
    ruleset_name: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleSetManagementService = Depends(get_ruleset_management_service_dep),
) -> None:
    """Delete a ruleset."""
    logger.info(
        "API delete ruleset request", correlation_id=correlation_id, ruleset_name=ruleset_name
    )
    service.delete_ruleset(ruleset_name)
    logger.info(
        "API delete ruleset completed", correlation_id=correlation_id, ruleset_name=ruleset_name
    )
