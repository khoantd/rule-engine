"""
API routes for workflow management (CRUD operations and listing).

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from api.deps import get_correlation_id, get_workflow_management_service_dep
from api.middleware.auth import get_api_key
from api.models import (
    ErrorResponse,
    WorkflowCreateRequest,
    WorkflowResponse,
    WorkflowsListResponse,
    WorkflowUpdateRequest,
)
from common.exceptions import NotFoundError
from common.logger import get_logger
from services.workflow_management import WorkflowManagementService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["workflows"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow",
    description="Create a new workflow definition with ordered stages.",
)
async def create_workflow(
    request: WorkflowCreateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: WorkflowManagementService = Depends(get_workflow_management_service_dep),
) -> WorkflowResponse:
    """Create a new workflow definition."""
    logger.info(
        "API create workflow request",
        correlation_id=correlation_id,
        workflow_name=request.name,
    )
    workflow_dict = service.create_workflow(request.model_dump(exclude_none=False))
    logger.info(
        "API create workflow completed",
        correlation_id=correlation_id,
        workflow_name=request.name,
    )
    return WorkflowResponse(**workflow_dict)


@router.get(
    "",
    response_model=WorkflowsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workflows",
    description="List workflows with optional active filter and pagination.",
)
async def list_workflows(
    correlation_id: Optional[str] = Depends(get_correlation_id),
    is_active: Optional[bool] = None,
    offset: int = 0,
    limit: int = 50,
    api_key: Optional[str] = Depends(get_api_key),
    service: WorkflowManagementService = Depends(get_workflow_management_service_dep),
) -> WorkflowsListResponse:
    """List workflows."""
    logger.info(
        "API list workflows request",
        correlation_id=correlation_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    result = service.list_workflows(is_active=is_active, offset=offset, limit=limit)
    workflows = [WorkflowResponse(**workflow_dict) for workflow_dict in result["workflows"]]
    logger.info(
        "API list workflows completed",
        correlation_id=correlation_id,
        count=result["count"],
    )
    return WorkflowsListResponse(workflows=workflows, count=result["count"])


@router.get(
    "/{name}",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workflow by name",
    description="Retrieve a workflow definition by its name.",
)
async def get_workflow(
    name: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: WorkflowManagementService = Depends(get_workflow_management_service_dep),
) -> WorkflowResponse:
    """Get a workflow by name."""
    logger.info(
        "API get workflow request",
        correlation_id=correlation_id,
        workflow_name=name,
    )
    workflow_dict = service.get_workflow(name)
    if not workflow_dict:
        logger.warning(
            "Workflow not found",
            correlation_id=correlation_id,
            workflow_name=name,
        )
        raise NotFoundError(
            f"Workflow with name '{name}' not found",
            error_code="WORKFLOW_NOT_FOUND",
            context={"name": name},
        )
    logger.info(
        "API get workflow completed",
        correlation_id=correlation_id,
        workflow_name=name,
    )
    return WorkflowResponse(**workflow_dict)


@router.put(
    "/{name}",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Update workflow",
    description="Update an existing workflow definition.",
)
async def update_workflow(
    name: str,
    request: WorkflowUpdateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: WorkflowManagementService = Depends(get_workflow_management_service_dep),
) -> WorkflowResponse:
    """Update an existing workflow."""
    logger.info(
        "API update workflow request",
        correlation_id=correlation_id,
        workflow_name=name,
    )
    update_data = request.model_dump(exclude_none=True)
    workflow_dict = service.update_workflow(name, update_data)
    logger.info(
        "API update workflow completed",
        correlation_id=correlation_id,
        workflow_name=name,
    )
    return WorkflowResponse(**workflow_dict)


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete (deactivate) workflow",
    description=(
        "Deactivate a workflow by name (soft delete). "
        "Implementations may optionally support hard delete via ?hard=true."
    ),
)
async def delete_workflow(
    name: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    hard: bool = False,
    api_key: Optional[str] = Depends(get_api_key),
    service: WorkflowManagementService = Depends(get_workflow_management_service_dep),
) -> None:
    """Delete (deactivate) a workflow."""
    logger.info(
        "API delete workflow request",
        correlation_id=correlation_id,
        workflow_name=name,
        hard=hard,
    )
    service.delete_workflow(name, hard=hard)
    logger.info(
        "API delete workflow completed",
        correlation_id=correlation_id,
        workflow_name=name,
        hard=hard,
    )
