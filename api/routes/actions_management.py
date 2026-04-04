"""
API routes for Actions/Patterns management (CRUD operations).

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from api.deps import get_actions_management_service_dep, get_correlation_id
from api.middleware.auth import get_api_key
from api.models import (
    ActionCreateRequest,
    ActionResponse,
    ActionsListResponse,
    ActionUpdateRequest,
    ErrorResponse,
)
from common.exceptions import NotFoundError
from common.logger import get_logger
from services.actions_management import ActionsManagementService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/actions",
    tags=["actions-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.get(
    "",
    response_model=ActionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all actions",
    description="Retrieve a list of all configured actions/patterns.",
)
async def list_actions(
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ActionsManagementService = Depends(get_actions_management_service_dep),
) -> ActionsListResponse:
    """List all actions/patterns."""
    logger.info("API list actions request", correlation_id=correlation_id)
    actions_data = service.list_actions()
    actions_metadata = service.list_actions_with_metadata()
    logger.info(
        "API list actions completed",
        correlation_id=correlation_id,
        count=len(actions_data),
    )
    items = [
        ActionResponse(
            id=details.get("id"),
            pattern=details["pattern"],
            message=details["message"],
            ruleset_id=details.get("ruleset_id"),
        )
        for details in actions_metadata.values()
    ]
    return ActionsListResponse(
        actions=actions_data,
        count=len(actions_data),
        items=items,
    )


@router.get(
    "/{pattern}",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an action by pattern",
    description="Retrieve a specific action by its pattern string.",
)
async def get_action(
    pattern: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ActionsManagementService = Depends(get_actions_management_service_dep),
) -> ActionResponse:
    """Get an action by pattern."""
    logger.info("API get action request", correlation_id=correlation_id, pattern=pattern)
    details = service.get_action_details(pattern)
    if not details:
        logger.warning("Action not found", correlation_id=correlation_id, pattern=pattern)
        raise NotFoundError(
            f"Action with pattern '{pattern}' not found",
            error_code="ACTION_NOT_FOUND",
            context={"pattern": pattern},
        )
    logger.info("API get action completed", correlation_id=correlation_id, pattern=pattern)
    return ActionResponse(
        id=details.get("id"),
        pattern=details["pattern"],
        message=details["message"],
        ruleset_id=details.get("ruleset_id"),
    )


@router.post(
    "",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new action",
    description="Create a new action/pattern with the provided configuration.",
)
async def create_action(
    request: ActionCreateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ActionsManagementService = Depends(get_actions_management_service_dep),
) -> ActionResponse:
    """Create a new action/pattern."""
    logger.info("API create action request", correlation_id=correlation_id, pattern=request.pattern)
    created_action = service.create_action(request.pattern, request.message)
    pattern_key = list(created_action.keys())[0]
    details = service.get_action_details(pattern_key)
    if not details:
        logger.warning(
            "Created action but failed to load details",
            correlation_id=correlation_id,
            pattern=pattern_key,
        )
        return ActionResponse(pattern=pattern_key, message=created_action[pattern_key])
    logger.info("API create action completed", correlation_id=correlation_id, pattern=pattern_key)
    return ActionResponse(
        id=details.get("id"),
        pattern=details["pattern"],
        message=details["message"],
        ruleset_id=details.get("ruleset_id"),
    )


@router.put(
    "/{pattern}",
    response_model=ActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing action",
    description=(
        "Update an existing action/pattern with a new message and optionally a new "
        "pattern string."
    ),
)
async def update_action(
    pattern: str,
    request: ActionUpdateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ActionsManagementService = Depends(get_actions_management_service_dep),
) -> ActionResponse:
    """Update an existing action/pattern."""
    logger.info("API update action request", correlation_id=correlation_id, pattern=pattern)
    updated_action = service.update_action(pattern, request.message, request.pattern)
    pattern_key = list(updated_action.keys())[0]
    details = service.get_action_details(pattern_key)
    if not details:
        logger.warning(
            "Updated action but failed to load details",
            correlation_id=correlation_id,
            pattern=pattern_key,
        )
        return ActionResponse(pattern=pattern_key, message=updated_action[pattern_key])
    logger.info("API update action completed", correlation_id=correlation_id, pattern=pattern)
    return ActionResponse(
        id=details.get("id"),
        pattern=details["pattern"],
        message=details["message"],
        ruleset_id=details.get("ruleset_id"),
    )


@router.delete(
    "/{pattern}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an action",
    description="Delete an action/pattern by its pattern string.",
)
async def delete_action(
    pattern: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: ActionsManagementService = Depends(get_actions_management_service_dep),
) -> None:
    """Delete an action/pattern."""
    logger.info("API delete action request", correlation_id=correlation_id, pattern=pattern)
    service.delete_action(pattern)
    logger.info("API delete action completed", correlation_id=correlation_id, pattern=pattern)
