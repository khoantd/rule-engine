"""
API routes for hot reload.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends

from pydantic import BaseModel, Field

from api.middleware.auth import get_api_key
from services.hot_reload import get_hot_reload_service
from common.exceptions import DataValidationError, ConfigurationError
from common.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/rules/hot-reload",
    tags=["hot-reload"],
    responses={
        400: {"model": Dict[str, Any], "description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"model": Dict[str, Any], "description": "Internal Server Error"},
    },
)


class ReloadRequest(BaseModel):
    """Request model for triggering rule reload."""

    ruleset_id: Optional[int] = Field(
        None, description="Optional ruleset ID to reload", ge=1
    )
    rule_id: Optional[str] = Field(None, description="Optional rule ID to reload")
    force: bool = Field(False, description="Force reload even if no changes detected")
    validate: bool = Field(True, description="Validate rules before reloading")


class ReloadStatusRequest(BaseModel):
    """Request model for getting reload status."""

    include_registry: bool = Field(
        True, description="Include registry statistics in status"
    )


class StartMonitoringRequest(BaseModel):
    """Request model for starting hot reload monitoring."""

    enabled: bool = Field(True, description="Enable automatic reloading")
    interval_seconds: Optional[int] = Field(
        30, description="Check interval in seconds", ge=5, le=3600
    )


@router.get(
    "/status",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get hot reload status",
    description="Get the current status of the hot reload service.",
)
async def get_hot_reload_status(
    include_registry: bool = True,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Get hot reload service status.

    Args:
        include_registry: Include registry statistics

    Returns:
        Status dictionary

    Raises:
        HTTPException: If status retrieval fails
    """
    logger.info("Getting hot reload status", include_registry=include_registry)

    try:
        service = get_hot_reload_service()
        status_dict = service.get_status()

        if not include_registry:
            status_dict.pop("registry", None)

        return status_dict

    except Exception as e:
        logger.error("Failed to get hot reload status", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "STATUS_ERROR",
            },
        )


@router.post(
    "/reload",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Reload rules",
    description="Reload rules from database into memory.",
)
async def reload_rules(
    request: ReloadRequest,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Reload rules.

    Args:
        request: Reload request

    Returns:
        Reload result dictionary

    Raises:
        HTTPException: If reload fails
    """
    logger.info(
        "Manual rule reload requested",
        ruleset_id=request.ruleset_id,
        rule_id=request.rule_id,
        force=request.force,
        validate=request.validate,
    )

    try:
        service = get_hot_reload_service()
        result = service.reload_rules(
            ruleset_id=request.ruleset_id,
            rule_id=request.rule_id,
            force=request.force,
            validate=request.validate,
        )
        return result

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )

    except Exception as e:
        logger.error("Failed to reload rules", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "RELOAD_ERROR",
            },
        )


@router.post(
    "/reload/rule/{rule_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Reload a single rule",
    description="Reload a single rule from database into memory.",
)
async def reload_single_rule(
    rule_id: str,
    validate: bool = True,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Reload a single rule.

    Args:
        rule_id: Rule identifier
        validate: Validate rule before reloading

    Returns:
        Reload result dictionary

    Raises:
        HTTPException: If reload fails
    """
    logger.info(
        "Single rule reload requested",
        rule_id=rule_id,
        validate=validate,
    )

    try:
        service = get_hot_reload_service()
        result = service.reload_single_rule(rule_id=rule_id, validate=validate)
        return result

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )

    except Exception as e:
        logger.error(
            "Failed to reload single rule",
            rule_id=rule_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "SINGLE_RELOAD_ERROR",
            },
        )


@router.post(
    "/reload/ruleset/{ruleset_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Reload a ruleset",
    description="Reload all rules in a ruleset from database into memory.",
)
async def reload_ruleset(
    ruleset_id: int,
    validate: bool = True,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Reload a ruleset.

    Args:
        ruleset_id: Ruleset identifier
        validate: Validate rules before reloading

    Returns:
        Reload result dictionary

    Raises:
        HTTPException: If reload fails
    """
    logger.info(
        "Ruleset reload requested",
        ruleset_id=ruleset_id,
        validate=validate,
    )

    try:
        service = get_hot_reload_service()
        result = service.reload_ruleset(ruleset_id=ruleset_id)
        return result

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except ConfigurationError as e:
        logger.error("Configuration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )

    except Exception as e:
        logger.error(
            "Failed to reload ruleset",
            ruleset_id=ruleset_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "RULESET_RELOAD_ERROR",
            },
        )


@router.post(
    "/validate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Validate current rules",
    description="Validate the current rules in memory.",
)
async def validate_rules(
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Validate current rules.

    Returns:
        Validation result dictionary

    Raises:
        HTTPException: If validation fails
    """
    logger.info("Rule validation requested")

    try:
        service = get_hot_reload_service()
        result = service.validate_reload()
        return result

    except Exception as e:
        logger.error("Failed to validate rules", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "VALIDATION_ERROR",
            },
        )


@router.post(
    "/monitoring/start",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Start hot reload monitoring",
    description="Start the automatic hot reload monitoring thread.",
)
async def start_monitoring(
    request: StartMonitoringRequest = None,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, str]:
    """
    Start hot reload monitoring.

    Args:
        request: Start monitoring request

    Returns:
        Status message

    Raises:
        HTTPException: If start fails
    """
    enabled = request.enabled if request else True
    interval_seconds = request.interval_seconds if request else 30

    logger.info(
        "Starting hot reload monitoring",
        enabled=enabled,
        interval_seconds=interval_seconds,
    )

    try:
        service = get_hot_reload_service()
        service._auto_reload_enabled = enabled
        service._reload_interval_seconds = interval_seconds
        service.start()

        return {
            "status": "started",
            "message": "Hot reload monitoring started",
            "enabled": enabled,
            "interval_seconds": interval_seconds,
        }

    except Exception as e:
        logger.error(
            "Failed to start hot reload monitoring", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "MONITORING_START_ERROR",
            },
        )


@router.post(
    "/monitoring/stop",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Stop hot reload monitoring",
    description="Stop the automatic hot reload monitoring thread.",
)
async def stop_monitoring(
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, str]:
    """
    Stop hot reload monitoring.

    Returns:
        Status message

    Raises:
        HTTPException: If stop fails
    """
    logger.info("Stopping hot reload monitoring")

    try:
        service = get_hot_reload_service()
        service.stop()

        return {
            "status": "stopped",
            "message": "Hot reload monitoring stopped",
        }

    except Exception as e:
        logger.error(
            "Failed to stop hot reload monitoring", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "MONITORING_STOP_ERROR",
            },
        )


@router.get(
    "/history",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get reload history",
    description="Get the history of rule reloads.",
)
async def get_reload_history(
    limit: int = 10,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Get reload history.

    Args:
        limit: Maximum number of reloads to return

    Returns:
        Reload history dictionary

    Raises:
        HTTPException: If history retrieval fails
    """
    logger.info("Getting reload history", limit=limit)

    try:
        service = get_hot_reload_service()
        history = service.get_reload_history(limit=limit)

        return {
            "limit": limit,
            "count": len(history),
            "history": history,
        }

    except Exception as e:
        logger.error("Failed to get reload history", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "HISTORY_ERROR",
            },
        )
