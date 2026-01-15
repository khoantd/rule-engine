"""
Logging middleware for API requests and responses.
"""

import time
import uuid
from typing import Callable
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from common.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging API requests and responses.
    
    Logs:
    - Request method, path, query parameters
    - Response status code
    - Execution time
    - Correlation ID
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request through logging middleware."""
        # Generate correlation ID if not present
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Log request
        start_time = time.time()
        logger.info(
            "API request received",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params) if request.query_params else None,
            correlation_id=correlation_id,
            client_ip=request.client.host if request.client else None
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Add correlation ID to response header
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Log response
            logger.info(
                "API response sent",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id
            )
            
            return response
            
        except Exception as e:
            # Log error
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(
                "API request error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                exc_info=True
            )
            raise

