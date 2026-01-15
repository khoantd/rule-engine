"""
API routes for health checks.
"""

from datetime import datetime
import time
from fastapi import APIRouter
from api.models import HealthResponse
from common.config import get_config
from common.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="",
    tags=["health"]
)

# Track application start time
_app_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the API service."
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the health status of the API service including:
    - Status (healthy/unhealthy)
    - API version
    - Timestamp
    - Uptime in seconds
    - Environment name
    
    Returns:
        Health response with service status
    """
    try:
        config = get_config()
        uptime_seconds = time.time() - _app_start_time
        
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime_seconds,
            environment=config.environment
        )
        
        logger.debug("Health check requested", status=response.status, uptime_seconds=uptime_seconds)
        
        return response
        
    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            timestamp=datetime.utcnow(),
            uptime_seconds=None,
            environment=None
        )


@router.get(
    "/",
    summary="Root endpoint",
    description="Root endpoint that provides API information."
)
async def root():
    """
    Root endpoint.
    
    Returns basic API information.
    """
    return {
        "name": "Rule Engine API",
        "version": "1.0.0",
        "description": "REST API for Rule Engine service",
        "docs_url": "/docs",
        "health_url": "/health"
    }

