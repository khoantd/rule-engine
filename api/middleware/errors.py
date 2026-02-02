"""
Error handling middleware for API requests.
"""

from typing import Callable
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import Request as FastAPIRequest
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from common.exceptions import (
    RuleEngineException,
    DataValidationError,
    ConfigurationError,
    RuleEvaluationError,
    WorkflowError,
    SecurityError
)
from common.logger import get_logger
from api.models import ErrorResponse

logger = get_logger(__name__)


def create_error_response(
    error: Exception,
    status_code: int,
    correlation_id: str = None
) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        error: Exception instance
        status_code: HTTP status code
        correlation_id: Optional correlation ID
        
    Returns:
        JSONResponse with error details
    """
    error_data = None
    
    if isinstance(error, RuleEngineException):
        error_data = error.to_dict()
    elif isinstance(error, StarletteHTTPException) and isinstance(getattr(error, 'detail', None), dict):
        error_data = dict(error.detail)
    else:
        error_data = {
            'error_type': error.__class__.__name__,
            'message': str(error),
            'error_code': None,
            'context': {}
        }
    
    error_response = ErrorResponse(
        **error_data,
        correlation_id=correlation_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.
    
    Args:
        request: FastAPI request
        exc: Exception instance
        
    Returns:
        JSONResponse with error details
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    is_http_exc = isinstance(exc, StarletteHTTPException)
    status_code = getattr(exc, 'status_code', None) if is_http_exc else None

    if is_http_exc and status_code is not None and status_code < 500:
        if status_code == 404:
            logger.warning(
                "Not found",
                path=request.url.path,
                correlation_id=correlation_id,
            )
        else:
            logger.warning(
                "Client error response",
                status_code=status_code,
                path=request.url.path,
                correlation_id=correlation_id,
            )
    else:
        logger.error(
            "Unhandled exception in API",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
            correlation_id=correlation_id,
            exc_info=True
        )
    
    # Handle specific exception types
    if isinstance(exc, DataValidationError):
        return create_error_response(exc, 400, correlation_id)
    elif isinstance(exc, ConfigurationError):
        return create_error_response(exc, 500, correlation_id)
    elif isinstance(exc, RuleEvaluationError):
        return create_error_response(exc, 500, correlation_id)
    elif isinstance(exc, WorkflowError):
        return create_error_response(exc, 500, correlation_id)
    elif isinstance(exc, SecurityError):
        return create_error_response(exc, 403, correlation_id)
    elif isinstance(exc, RuleEngineException):
        return create_error_response(exc, 500, correlation_id)
    elif isinstance(exc, StarletteHTTPException):
        return create_error_response(exc, exc.status_code, correlation_id)
    else:
        # Generic error for unhandled exceptions
        return create_error_response(
            Exception("Internal server error"),
            500,
            correlation_id
        )


def validation_exception_handler(request: FastAPIRequest, exc: RequestValidationError) -> FastAPIJSONResponse:
    """
    Handler for request validation errors.
    
    Args:
        request: FastAPI request
        exc: Validation exception
        
    Returns:
        JSONResponse with validation error details
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.warning(
        "Request validation error",
        errors=exc.errors(),
        path=request.url.path,
        correlation_id=correlation_id
    )
    
    error_response = ErrorResponse(
        error_type="ValidationError",
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        context={"errors": exc.errors()},
        correlation_id=correlation_id
    )
    
    return FastAPIJSONResponse(
        status_code=422,
        content=error_response.dict()
    )

