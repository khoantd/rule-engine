"""
API routes for rule versioning.

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from api.deps import get_rule_versioning_service_dep
from api.middleware.auth import get_api_key
from common.logger import get_logger
from services.rule_versioning import RuleVersioningService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/rules/versions",
    tags=["rule-versioning"],
    responses={
        400: {"model": Dict[str, Any], "description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"model": Dict[str, Any], "description": "Internal Server Error"},
    },
)


class VersionCompareRequest(BaseModel):
    """Request model for comparing two versions."""

    version_a: int = Field(..., description="First version number", ge=1)
    version_b: int = Field(..., description="Second version number", ge=1)


class RollbackRequest(BaseModel):
    """Request model for rolling back to a version."""

    version_number: int = Field(..., description="Version number to rollback to", ge=1)
    change_reason: Optional[str] = Field(None, description="Reason for the rollback")


@router.get(
    "/{rule_id}",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get version history for a rule",
    description="Retrieve the complete version history for a specific rule.",
)
async def get_version_history(
    rule_id: str,
    limit: Optional[int] = None,
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleVersioningService = Depends(get_rule_versioning_service_dep),
) -> List[Dict[str, Any]]:
    """Get version history for a rule."""
    logger.info("Getting version history", rule_id=rule_id, limit=limit)
    return service.get_version_history(rule_id=rule_id, limit=limit)


@router.get(
    "/{rule_id}/current",
    response_model=Optional[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get current version of a rule",
    description="Retrieve the current (latest) version of a specific rule.",
)
async def get_current_version(
    rule_id: str,
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleVersioningService = Depends(get_rule_versioning_service_dep),
) -> Optional[Dict[str, Any]]:
    """Get current version of a rule."""
    logger.info("Getting current version", rule_id=rule_id)
    return service.get_current_version(rule_id=rule_id)


@router.get(
    "/{rule_id}/{version_number}",
    response_model=Optional[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get a specific version of a rule",
    description="Retrieve a specific version of a rule by version number.",
)
async def get_version(
    rule_id: str,
    version_number: int,
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleVersioningService = Depends(get_rule_versioning_service_dep),
) -> Optional[Dict[str, Any]]:
    """Get a specific version of a rule."""
    logger.info("Getting specific version", rule_id=rule_id, version_number=version_number)
    return service.get_version(rule_id=rule_id, version_number=version_number)


@router.post(
    "/{rule_id}/compare",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Compare two rule versions",
    description="Compare two versions of a rule to see differences.",
)
async def compare_versions(
    rule_id: str,
    request: VersionCompareRequest,
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleVersioningService = Depends(get_rule_versioning_service_dep),
) -> Dict[str, Any]:
    """Compare two versions of a rule."""
    logger.info(
        "Comparing versions",
        rule_id=rule_id,
        version_a=request.version_a,
        version_b=request.version_b,
    )
    return service.compare_versions(
        rule_id=rule_id,
        version_a=request.version_a,
        version_b=request.version_b,
    )


@router.post(
    "/{rule_id}/rollback",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Rollback a rule to a specific version",
    description="Rollback a rule to a specific previous version.",
)
async def rollback_rule(
    rule_id: str,
    request: RollbackRequest,
    api_key: Optional[str] = Depends(get_api_key),
    service: RuleVersioningService = Depends(get_rule_versioning_service_dep),
) -> Dict[str, Any]:
    """Rollback a rule to a specific version."""
    logger.info(
        "Rolling back rule",
        rule_id=rule_id,
        version_number=request.version_number,
        change_reason=request.change_reason,
    )
    return service.rollback_to_version(
        rule_id=rule_id,
        version_number=request.version_number,
        change_reason=request.change_reason,
    )
