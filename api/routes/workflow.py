"""
API routes for workflow execution.
"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowNamedExecutionRequest,
    ErrorResponse,
)
from services.workflow_exec import wf_exec
from services.workflow_management import get_workflow_management_service
from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    WorkflowError
)
from api.middleware.auth import get_api_key

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/workflow",
    tags=["workflow"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.post(
    "/execute",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute workflow",
    description="Execute a multi-stage workflow with the provided process name, stages, and input data."
)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key)
) -> WorkflowExecutionResponse:
    """
    Execute workflow with given process name, stages, and data.
    
    This endpoint executes a multi-stage workflow using the Chain of Responsibility
    pattern. Each stage processes the data through its handler and passes the
    result to the next stage.
    
    Args:
        request: Workflow execution request with process name, stages, and data
        http_request: FastAPI request object for correlation ID
        
    Returns:
        Workflow execution response with final result
        
    Raises:
        HTTPException: If execution fails or validation fails
    """
    start_time = time.time()
    correlation_id = getattr(http_request.state, 'correlation_id', None)
    
    logger.info(
        "API workflow execution request",
        correlation_id=correlation_id,
        process_name=request.process_name,
        stages=request.stages,
        data_keys=list(request.data.keys())
    )
    
    try:
        # Execute workflow
        result = wf_exec(
            process_name=request.process_name,
            ls_stages=request.stages,
            data=request.data
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        response = WorkflowExecutionResponse(
            process_name=request.process_name,
            stages=request.stages if request.stages else ["INITIATED", "NEW", "INPROGESS", "FINISHED"],
            result=result,
            execution_time_ms=execution_time_ms
        )
        
        logger.info(
            "API workflow execution completed",
            correlation_id=correlation_id,
            process_name=request.process_name,
            execution_time_ms=execution_time_ms
        )
        
        return response
        
    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict()
        )
    except WorkflowError as e:
        logger.error("Workflow error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict()
        )
    except Exception as e:
        logger.error("Unexpected error in workflow execution", error=str(e), correlation_id=correlation_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR"
            }
        )


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
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> WorkflowExecutionResponse:
    """
    Execute a workflow by its stored definition name.

    This endpoint:
    1. Looks up workflow definition by workflow_name (must be active).
    2. Extracts ordered stage names from the definition.
    3. Invokes wf_exec with process_name=workflow_name and ls_stages=stages.

    Args:
        request: WorkflowNamedExecutionRequest containing workflow_name and data.
        http_request: FastAPI request for correlation ID.

    Returns:
        WorkflowExecutionResponse with execution result.
    """
    start_time = time.time()
    correlation_id = getattr(http_request.state, "correlation_id", None)

    logger.info(
        "API workflow execute-by-name request",
        correlation_id=correlation_id,
        workflow_name=request.workflow_name,
        data_keys=list(request.data.keys()),
    )

    try:
        service = get_workflow_management_service()
        workflow_dict = service.get_workflow(request.workflow_name)
        if not workflow_dict or not workflow_dict.get("is_active", False):
            logger.warning(
                "Workflow not found or inactive for execute-by-name",
                correlation_id=correlation_id,
                workflow_name=request.workflow_name,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Workflow with name '{request.workflow_name}' not found or inactive",
                    "error_code": "WORKFLOW_NOT_FOUND",
                    "context": {"name": request.workflow_name},
                },
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
    except DataValidationError as exc:
        logger.error(
            "Data validation error in execute-by-name",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.to_dict(),
        )
    except WorkflowError as exc:
        logger.error(
            "Workflow error in execute-by-name",
            error=str(exc),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.to_dict(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error in workflow execute-by-name",
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

