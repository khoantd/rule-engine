"""
API routes for workflow execution.
"""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    ErrorResponse
)
from services.workflow_exec import wf_exec
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

