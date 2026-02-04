"""
API routes for workflow management (CRUD operations and listing).

This module provides REST API endpoints for managing workflow definitions:
- Create workflow
- List workflows
- Get workflow by name
- Update workflow
- Delete (deactivate) workflow
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowResponse,
    WorkflowsListResponse,
    ErrorResponse,
)
from services.workflow_management import get_workflow_management_service
from common.logger import get_logger
from common.exceptions import DataValidationError, ConfigurationError
from api.middleware.auth import get_api_key

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
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> WorkflowResponse:
    """
    Create a new workflow definition.

    Args:
        request: Workflow creation request
        http_request: FastAPI request for correlation ID

    Returns:
        Created workflow definition

    Raises:
        HTTPException: On validation or server errors
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)
    logger.info(
        "API create workflow request",
        correlation_id=correlation_id,
        workflow_name=request.name,
    )

    try:
        service = get_workflow_management_service()
        workflow_dict = service.create_workflow(request.dict(exclude_none=False))
        logger.info(
            "API create workflow completed",
            correlation_id=correlation_id,
            workflow_name=request.name,
        )
        return WorkflowResponse(**workflow_dict)
    except DataValidationError as exc:
        logger.error(
            "Data validation error creating workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.to_dict(),
        )
    except ConfigurationError as exc:
        logger.error(
            "Configuration error creating workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.to_dict(),
        )
    except Exception as exc:
        logger.error(
            "Unexpected error creating workflow",
            error=str(exc),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(exc).__name__,
                "message": str(exc),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


@router.get(
    "",
    response_model=WorkflowsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workflows",
    description="List workflows with optional active filter and pagination.",
)
async def list_workflows(
    http_request: Request,
    is_active: Optional[bool] = None,
    offset: int = 0,
    limit: int = 50,
    api_key: Optional[str] = Depends(get_api_key),
) -> WorkflowsListResponse:
    """
    List workflows.

    Args:
        http_request: FastAPI request for correlation ID
        is_active: Optional filter for active flag
        offset: Pagination offset
        limit: Page size

    Returns:
        WorkflowsListResponse with workflows and count
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)
    logger.info(
        "API list workflows request",
        correlation_id=correlation_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )

    try:
        service = get_workflow_management_service()
        result = service.list_workflows(
            is_active=is_active,
            offset=offset,
            limit=limit,
        )
        workflows = [
            WorkflowResponse(**workflow_dict) for workflow_dict in result["workflows"]
        ]
        logger.info(
            "API list workflows completed",
            correlation_id=correlation_id,
            count=result["count"],
        )
        return WorkflowsListResponse(workflows=workflows, count=result["count"])
    except ConfigurationError as exc:
        logger.error(
            "Configuration error listing workflows",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.to_dict(),
        )
    except Exception as exc:
        logger.error(
            "Unexpected error listing workflows",
            error=str(exc),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(exc).__name__,
                "message": str(exc),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


@router.get(
    "/{name}",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workflow by name",
    description="Retrieve a workflow definition by its name.",
)
async def get_workflow(
    name: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> WorkflowResponse:
    """
    Get a workflow by name.

    Args:
        name: Workflow name
        http_request: FastAPI request for correlation ID

    Returns:
        Workflow definition

    Raises:
        HTTPException: 404 if not found
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)
    logger.info(
        "API get workflow request",
        correlation_id=correlation_id,
        workflow_name=name,
    )

    try:
        service = get_workflow_management_service()
        workflow_dict = service.get_workflow(name)
        if not workflow_dict:
            logger.warning(
                "Workflow not found",
                correlation_id=correlation_id,
                workflow_name=name,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Workflow with name '{name}' not found",
                    "error_code": "WORKFLOW_NOT_FOUND",
                    "context": {"name": name},
                },
            )

        logger.info(
            "API get workflow completed",
            correlation_id=correlation_id,
            workflow_name=name,
        )
        return WorkflowResponse(**workflow_dict)
    except DataValidationError as exc:
        logger.error(
            "Data validation error getting workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.to_dict(),
        )
    except HTTPException:
        raise
    except ConfigurationError as exc:
        logger.error(
            "Configuration error getting workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.to_dict(),
        )
    except Exception as exc:
        logger.error(
            "Unexpected error getting workflow",
            error=str(exc),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(exc).__name__,
                "message": str(exc),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


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
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> WorkflowResponse:
    """
    Update an existing workflow.

    Args:
        name: Workflow name
        request: Workflow update payload
        http_request: FastAPI request for correlation ID

    Returns:
        Updated workflow definition
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)
    logger.info(
        "API update workflow request",
        correlation_id=correlation_id,
        workflow_name=name,
    )

    try:
        service = get_workflow_management_service()
        update_data = request.dict(exclude_none=True)
        workflow_dict = service.update_workflow(name, update_data)
        logger.info(
            "API update workflow completed",
            correlation_id=correlation_id,
            workflow_name=name,
        )
        return WorkflowResponse(**workflow_dict)
    except DataValidationError as exc:
        status_code = status.HTTP_404_NOT_FOUND if exc.error_code == "WORKFLOW_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
        logger.error(
            "Data validation error updating workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status_code,
            detail=exc.to_dict(),
        )
    except ConfigurationError as exc:
        logger.error(
            "Configuration error updating workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.to_dict(),
        )
    except Exception as exc:
        logger.error(
            "Unexpected error updating workflow",
            error=str(exc),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(exc).__name__,
                "message": str(exc),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


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
    http_request: Request,
    hard: bool = False,
    api_key: Optional[str] = Depends(get_api_key),
) -> None:
    """
    Delete (deactivate) a workflow.

    Args:
        name: Workflow name
        http_request: FastAPI request for correlation ID
        hard: If true, perform a hard delete

    Raises:
        HTTPException: 404 if workflow not found
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)
    logger.info(
        "API delete workflow request",
        correlation_id=correlation_id,
        workflow_name=name,
        hard=hard,
    )

    try:
        service = get_workflow_management_service()
        service.delete_workflow(name, hard=hard)
        logger.info(
            "API delete workflow completed",
            correlation_id=correlation_id,
            workflow_name=name,
            hard=hard,
        )
    except DataValidationError as exc:
        status_code = status.HTTP_404_NOT_FOUND if exc.error_code == "WORKFLOW_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
        logger.error(
            "Data validation error deleting workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status_code,
            detail=exc.to_dict(),
        )
    except ConfigurationError as exc:
        logger.error(
            "Configuration error deleting workflow",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.to_dict(),
        )
    except Exception as exc:
        logger.error(
            "Unexpected error deleting workflow",
            error=str(exc),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(exc).__name__,
                "message": str(exc),
                "error_code": "UNEXPECTED_ERROR",
            },
        )

