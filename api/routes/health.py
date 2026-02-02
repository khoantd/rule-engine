"""
API routes for health checks.
"""

from datetime import datetime
import time
from typing import Any, Dict, Optional
from fastapi import APIRouter
from api.models import HealthResponse
from common.config import get_config
from common.logger import get_logger
from services.hot_reload import get_hot_reload_service
from common.rule_registry import get_rule_registry

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["health"])

# Track application start time
_app_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the API service.",
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
            environment=config.environment,
        )

        logger.debug(
            "Health check requested",
            status=response.status,
            uptime_seconds=uptime_seconds,
        )

        return response

    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            timestamp=datetime.utcnow(),
            uptime_seconds=None,
            environment=None,
        )


@router.get(
    "/",
    summary="Root endpoint",
    description="Root endpoint that provides API information.",
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
        "health_url": "/health",
    }


@router.get(
    "/health/hot-reload",
    summary="Hot reload health check",
    description="Check health status of hot reload service.",
)
async def hot_reload_health_check() -> Dict[str, Any]:
    """
    Hot reload health check endpoint.

    Returns:
        Hot reload health status including:
        - status: Health status (healthy/unhealthy)
        - monitoring_active: Whether monitoring is active
        - last_reload: Last reload timestamp
        - registry_stats: Registry statistics
        - reload_count: Total reload count
    """
    try:
        service = get_hot_reload_service()
        registry = get_rule_registry()

        status_dict = service.get_status()

        # Determine overall health
        is_healthy = (
            status_dict.get("monitoring_active", False)
            or status_dict.get("last_reload_status") == "success"
        )

        # Check if registry has rules
        registry_stats = registry.get_stats()
        if registry_stats.get("rule_count", 0) == 0:
            is_healthy = False

        result = {
            "status": "healthy" if is_healthy else "unhealthy",
            "monitoring_active": status_dict.get("monitoring_active", False),
            "auto_reload_enabled": status_dict.get("auto_reload_enabled", False),
            "last_reload": status_dict.get("last_reload"),
            "reload_count": status_dict.get("reload_count", 0),
            "last_reload_status": status_dict.get("last_reload_status"),
            "registry": {
                "rule_count": registry_stats.get("rule_count", 0),
                "ruleset_count": registry_stats.get("ruleset_count", 0),
                "version": registry_stats.get("version", 0),
                "last_reload": registry_stats.get("last_reload"),
            },
            "checks": {
                "monitoring_active": status_dict.get("monitoring_active", False),
                "registry_has_rules": registry_stats.get("rule_count", 0) > 0,
                "last_reload_successful": status_dict.get("last_reload_status")
                == "success",
            },
        }

        logger.debug("Hot reload health check completed", status=result["status"])

        return result

    except Exception as e:
        logger.error("Hot reload health check failed", error=str(e), exc_info=True)

        return {
            "status": "unhealthy",
            "error": str(e),
            "checks": {
                "monitoring_active": False,
                "registry_has_rules": False,
                "last_reload_successful": False,
            },
        }
