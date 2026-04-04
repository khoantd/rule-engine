"""
API routes for workflow execution.

Domain exceptions propagate to ``api.middleware.errors``.
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, status

from api.deps import get_correlation_id, get_workflow_management_service_dep
from api.middleware.auth import get_api_key
from api.models import (
    ErrorResponse,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowNamedExecutionRequest,
)
from common.exceptions import NotFoundError
from common.logger import get_logger
from services.workflow_exec import wf_exec
from services.workflow_management import WorkflowManagementService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/workflow",
    tags=["workflow"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.post(
    "/execute",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute workflow",
    description=(
        "Execute a multi-stage workflow with the provided process name, stages, and input data."
    ),
)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
) -> WorkflowExecutionResponse:
    """Execute workflow with given process name, stages, and data."""
    start_time = time.time()
    logger.info(
        "API workflow execution request",
        correlation_id=correlation_id,
        process_name=request.process_name,
        stages=request.stages,
        data_keys=list(request.data.keys()),
    )
    result = wf_exec(
        process_name=request.process_name,
        ls_stages=request.stages,
        data=request.data,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    response = WorkflowExecutionResponse(
        process_name=request.process_name,
        stages=request.stages if request.stages else ["INITIATED", "NEW", "INPROGESS", "FINISHED"],
        result=result,
        execution_time_ms=execution_time_ms,
    )
    logger.info(
        "API workflow execution completed",
        correlation_id=correlation_id,
        process_name=request.process_name,
        execution_time_ms=execution_time_ms,
    )
    return response


@router.post(
    "/execute-by-name",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute workflow by name",
    description=(
        "Execute a stored workflow definition by its name. "
        "Stages are loaded from the workflow definition."
    ),
)
async def execute_workflow_by_name(
    request: WorkflowNamedExecutionRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: WorkflowManagementService = Depends(get_workflow_management_service_dep),
) -> WorkflowExecutionResponse:
    """Execute a workflow by its stored definition name."""
    start_time = time.time()
    logger.info(
        "API workflow execute-by-name request",
        correlation_id=correlation_id,
        workflow_name=request.workflow_name,
        data_keys=list(request.data.keys()),
    )
    workflow_dict = service.get_workflow(request.workflow_name)
    if not workflow_dict or not workflow_dict.get("is_active", False):
        logger.warning(
            "Workflow not found or inactive for execute-by-name",
            correlation_id=correlation_id,
            workflow_name=request.workflow_name,
        )
        raise NotFoundError(
            f"Workflow with name '{request.workflow_name}' not found or inactive",
            error_code="WORKFLOW_NOT_FOUND",
            context={"name": request.workflow_name},
        )
    stages = [stage["name"] for stage in workflow_dict.get("stages", [])]
    logger.debug(
        "Executing workflow by name",
        correlation_id=correlation_id,
        workflow_name=request.workflow_name,
        stages=stages,
    )
    result = wf_exec(
        process_name=request.workflow_name,
        ls_stages=stages,
        data=request.data,
    )
    execution_time_ms = (time.time() - start_time) * 1000
    response = WorkflowExecutionResponse(
        process_name=request.workflow_name,
        stages=stages,
        result=result,
        execution_time_ms=execution_time_ms,
    )
    logger.info(
        "API workflow execute-by-name completed",
        correlation_id=correlation_id,
        workflow_name=request.workflow_name,
        execution_time_ms=execution_time_ms,
    )
    return response
