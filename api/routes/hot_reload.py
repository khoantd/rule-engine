"""
API routes for hot reload.

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from api.deps import get_hot_reload_service_dep
from api.middleware.auth import get_api_key
from common.logger import get_logger
from services.hot_reload import HotReloadService

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

    ruleset_id: Optional[int] = Field(None, description="Optional ruleset ID to reload", ge=1)
    rule_id: Optional[str] = Field(None, description="Optional rule ID to reload")
    force: bool = Field(False, description="Force reload even if no changes detected")
    validate_before_reload: bool = Field(
        True,
        description="Validate rules before reloading",
        validation_alias="validate",
    )

    model_config = ConfigDict(populate_by_name=True)


class ValidateFromSourceRequest(BaseModel):
    """Request model for validating rules from config repository (e.g. DB)."""

    source: Optional[str] = Field(
        None,
        description="Optional source: ruleset name (DB) or file path (file repo). Default uses config.",
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
    service: HotReloadService = Depends(get_hot_reload_service_dep),
) -> Dict[str, Any]:
    """Get hot reload service status."""
    logger.info("Getting hot reload status", include_registry=include_registry)
    status_dict = service.get_status()
    if not include_registry:
        status_dict.pop("registry", None)
    return status_dict


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
    service: HotReloadService = Depends(get_hot_reload_service_dep),
) -> Dict[str, Any]:
    """Reload rules."""
    logger.info(
        "Manual rule reload requested",
        ruleset_id=request.ruleset_id,
        rule_id=request.rule_id,
        force=request.force,
        validate=request.validate_before_reload,
    )
    return service.reload_rules(
        ruleset_id=request.ruleset_id,
        rule_id=request.rule_id,
        force=request.force,
        validate=request.validate_before_reload,
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
    service: HotReloadService = Depends(get_hot_reload_service_dep),
) -> Dict[str, Any]:
    """Reload a single rule."""
    logger.info(
        "Single rule reload requested",
        rule_id=rule_id,
        validate=validate,
    )
    return service.reload_single_rule(rule_id=rule_id, validate=validate)


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
    service: HotReloadService = Depends(get_hot_reload_service_dep),
) -> Dict[str, Any]:
    """Reload a ruleset."""
    logger.info(
        "Ruleset reload requested",
        ruleset_id=ruleset_id,
        validate=validate,
    )
    return service.reload_ruleset(ruleset_id=ruleset_id)


@router.post(
    "/validate",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Validate current rules",
    description="Validate the current rules in memory.",
)
async def validate_rules(
    api_key: Optional[str] = Depends(get_api_key),
    service: HotReloadService = Depends(get_hot_reload_service_dep),
) -> Dict[str, Any]:
    """Validate current rules."""
    logger.info("Rule validation requested")
    return service.validate_reload()


@router.post(
    "/validate-from-source",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Validate rules from repository (e.g. DB)",
    description=(
        "Load rules and conditions from the config repository (database when "
        "USE_DATABASE=true) and validate. Returns invalid cases with rule name and "
        "related conditions in each error message."
    ),
)
async def validate_rules_from_source(
    api_key: Optional[str] = Depends(get_api_key),
    service: HotReloadService = Depends(get_hot_reload_service_dep),
    request: Optional[ValidateFromSourceRequest] = Body(None),
) -> Dict[str, Any]:
    """Validate rules from config repository (e.g. database)."""
    source = request.source if request is not None else None
    logger.info("Validate rules from source requested", source=source)
    return service.validate_from_source(source=source)


@router.post(
    "/monitoring/start",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Start hot reload monitoring",
    description="Start the automatic hot reload monitoring thread.",
)
async def start_monitoring(
    api_key: Optional[str] = Depends(get_api_key),
    service: HotReloadService = Depends(get_hot_reload_service_dep),
    request: Optional[StartMonitoringRequest] = Body(None),
) -> Dict[str, str]:
    """Start hot reload monitoring."""
    enabled = request.enabled if request else True
    interval_seconds = request.interval_seconds if request else 30

    logger.info(
        "Starting hot reload monitoring",
        enabled=enabled,
        interval_seconds=interval_seconds,
    )

    service._auto_reload_enabled = enabled
    service._reload_interval_seconds = interval_seconds
    service.start()

    return {
        "status": "started",
        "message": "Hot reload monitoring started",
        "enabled": str(enabled),
        "interval_seconds": str(interval_seconds),
    }


@router.post(
    "/monitoring/stop",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Stop hot reload monitoring",
    description="Stop the automatic hot reload monitoring thread.",
)
async def stop_monitoring(
    api_key: Optional[str] = Depends(get_api_key),
    service: HotReloadService = Depends(get_hot_reload_service_dep),
) -> Dict[str, str]:
    """Stop hot reload monitoring."""
    logger.info("Stopping hot reload monitoring")
    service.stop()
    return {
        "status": "stopped",
        "message": "Hot reload monitoring stopped",
    }


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
    service: HotReloadService = Depends(get_hot_reload_service_dep),
) -> Dict[str, Any]:
    """Get reload history."""
    logger.info("Getting reload history", limit=limit)
    history = service.get_reload_history(limit=limit)
    return {
        "limit": limit,
        "count": len(history),
        "history": history,
    }
