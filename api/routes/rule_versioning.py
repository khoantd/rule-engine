"""
API routes for rule versioning.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends

from pydantic import BaseModel, Field
from typing import Dict, Any

from api.middleware.auth import get_api_key
from services.rule_versioning import get_rule_versioning_service
from common.exceptions import DataValidationError, ConfigurationError
from common.logger import get_logger

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
) -> List[Dict[str, Any]]:
    """
    Get version history for a rule.

    Args:
        rule_id: Rule identifier
        limit: Maximum number of versions to return

    Returns:
        List of version dictionaries

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info("Getting version history", rule_id=rule_id, limit=limit)

    try:
        service = get_rule_versioning_service()
        versions = service.get_version_history(rule_id=rule_id, limit=limit)
        return versions

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), rule_id=rule_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to get version history", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "VERSION_HISTORY_ERROR",
            },
        )


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
) -> Optional[Dict[str, Any]]:
    """
    Get current version of a rule.

    Args:
        rule_id: Rule identifier

    Returns:
        Current version dictionary or None if not found

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info("Getting current version", rule_id=rule_id)

    try:
        service = get_rule_versioning_service()
        version = service.get_current_version(rule_id=rule_id)
        return version

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), rule_id=rule_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to get current version", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "CURRENT_VERSION_ERROR",
            },
        )


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
) -> Optional[Dict[str, Any]]:
    """
    Get a specific version of a rule.

    Args:
        rule_id: Rule identifier
        version_number: Version number

    Returns:
        Version dictionary or None if not found

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info(
        "Getting specific version", rule_id=rule_id, version_number=version_number
    )

    try:
        service = get_rule_versioning_service()
        version = service.get_version(rule_id=rule_id, version_number=version_number)
        return version

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), rule_id=rule_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to get version", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "VERSION_GET_ERROR",
            },
        )


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
) -> Dict[str, Any]:
    """
    Compare two versions of a rule.

    Args:
        rule_id: Rule identifier
        request: Comparison request with version numbers

    Returns:
        Comparison dictionary with differences

    Raises:
        HTTPException: If comparison fails
    """
    logger.info(
        "Comparing versions",
        rule_id=rule_id,
        version_a=request.version_a,
        version_b=request.version_b,
    )

    try:
        service = get_rule_versioning_service()
        comparison = service.compare_versions(
            rule_id=rule_id,
            version_a=request.version_a,
            version_b=request.version_b,
        )
        return comparison

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), rule_id=rule_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to compare versions", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "VERSION_COMPARE_ERROR",
            },
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
) -> Dict[str, Any]:
    """
    Rollback a rule to a specific version.

    Args:
        rule_id: Rule identifier
        request: Rollback request with version number and reason

    Returns:
        Updated rule dictionary

    Raises:
        HTTPException: If rollback fails
    """
    logger.info(
        "Rolling back rule",
        rule_id=rule_id,
        version_number=request.version_number,
        change_reason=request.change_reason,
    )

    try:
        service = get_rule_versioning_service()
        updated_rule = service.rollback_to_version(
            rule_id=rule_id,
            version_number=request.version_number,
            change_reason=request.change_reason,
        )
        return updated_rule

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e), rule_id=rule_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to rollback rule", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "ROLLBACK_ERROR",
            },
        )
