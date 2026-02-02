"""
API routes for A/B testing.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from starlette import status as http_status

from pydantic import BaseModel, Field
from typing import Dict, Any

from api.middleware.auth import get_api_key
from services.ab_testing import get_ab_testing_service
from common.exceptions import DataValidationError, ConfigurationError
from common.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/rules/ab-tests",
    tags=["ab-testing"],
    responses={
        400: {"model": Dict[str, Any], "description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"model": Dict[str, Any], "description": "Internal Server Error"},
    },
)


class CreateABTestRequest(BaseModel):
    """Request model for creating an A/B test."""

    test_id: str = Field(..., description="Unique test identifier")
    test_name: str = Field(..., description="Test name")
    rule_id: str = Field(..., description="Target rule ID")
    ruleset_id: int = Field(..., description="Ruleset ID", ge=1)
    variant_a_version: str = Field(
        ..., description="Version string for variant A (control)"
    )
    variant_b_version: str = Field(
        ..., description="Version string for variant B (treatment)"
    )
    description: Optional[str] = Field(None, description="Test description")
    traffic_split_a: float = Field(
        0.5, description="Traffic split for variant A (0-1)", ge=0, le=1
    )
    traffic_split_b: float = Field(
        0.5, description="Traffic split for variant B (0-1)", ge=0, le=1
    )
    variant_a_description: Optional[str] = Field(
        None, description="Description of variant A"
    )
    variant_b_description: Optional[str] = Field(
        None, description="Description of variant B"
    )
    duration_hours: Optional[int] = Field(
        None, description="Test duration in hours", ge=1
    )
    min_sample_size: Optional[int] = Field(
        None, description="Minimum sample size per variant", ge=1
    )
    confidence_level: float = Field(
        0.95, description="Statistical confidence level (0-1)", gt=0, le=1
    )
    tags: Optional[List[str]] = Field(None, description="Optional tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class StartABTestRequest(BaseModel):
    """Request model for starting an A/B test."""

    started_by: Optional[str] = Field(None, description="User starting the test")


class StopABTestRequest(BaseModel):
    """Request model for stopping an A/B test."""

    winning_variant: Optional[str] = Field(
        None, description="Winning variant ('A' or 'B')"
    )
    stopped_by: Optional[str] = Field(None, description="User stopping the test")


class AssignVariantRequest(BaseModel):
    """Request model for assigning a variant."""

    assignment_key: str = Field(
        ..., description="Key for assignment (user ID, session ID, etc.)"
    )


@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a new A/B test",
    description="Create a new A/B test to compare two rule versions.",
)
async def create_ab_test(
    request: CreateABTestRequest,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Create a new A/B test.

    Args:
        request: A/B test creation request

    Returns:
        Created test dictionary

    Raises:
        HTTPException: If creation fails
    """
    logger.info(
        "Creating A/B test",
        test_id=request.test_id,
        rule_id=request.rule_id,
        variant_a=request.variant_a_version,
        variant_b=request.variant_b_version,
    )

    try:
        service = get_ab_testing_service()
        test = service.create_test(
            test_id=request.test_id,
            test_name=request.test_name,
            rule_id=request.rule_id,
            ruleset_id=request.ruleset_id,
            variant_a_version=request.variant_a_version,
            variant_b_version=request.variant_b_version,
            description=request.description,
            traffic_split_a=request.traffic_split_a,
            traffic_split_b=request.traffic_split_b,
            variant_a_description=request.variant_a_description,
            variant_b_description=request.variant_b_description,
            duration_hours=request.duration_hours,
            min_sample_size=request.min_sample_size,
            confidence_level=request.confidence_level,
            tags=request.tags,
            metadata=request.metadata,
        )
        return test

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to create A/B test", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "TEST_CREATE_ERROR",
            },
        )


@router.get(
    "/",
    response_model=List[Dict[str, Any]],
    status_code=http_status.HTTP_200_OK,
    summary="List A/B tests",
    description="List all A/B tests with optional filters.",
)
async def list_ab_tests(
    rule_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    api_key: Optional[str] = Depends(get_api_key),
) -> List[Dict[str, Any]]:
    """
    List A/B tests.

    Args:
        rule_id: Optional rule ID filter
        status: Optional status filter
        limit: Maximum number of tests to return

    Returns:
        List of test dictionaries

    Raises:
        HTTPException: If listing fails
    """
    logger.info("Listing A/B tests", rule_id=rule_id, status=status, limit=limit)

    try:
        service = get_ab_testing_service()
        tests = service.list_tests(
            rule_id=rule_id,
            status=status,
            limit=limit,
        )
        return tests

    except Exception as e:
        logger.error("Failed to list A/B tests", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "TEST_LIST_ERROR",
            },
        )


@router.get(
    "/{test_id}",
    response_model=Optional[Dict[str, Any]],
    status_code=http_status.HTTP_200_OK,
    summary="Get an A/B test",
    description="Retrieve details of a specific A/B test.",
)
async def get_ab_test(
    test_id: str,
    api_key: Optional[str] = Depends(get_api_key),
) -> Optional[Dict[str, Any]]:
    """
    Get an A/B test.

    Args:
        test_id: Test identifier

    Returns:
        Test dictionary or None if not found

    Raises:
        HTTPException: If retrieval fails
    """
    logger.info("Getting A/B test", test_id=test_id)

    try:
        service = get_ab_testing_service()
        test = service.get_test(test_id=test_id)
        return test

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to get A/B test", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "TEST_GET_ERROR",
            },
        )


@router.post(
    "/{test_id}/start",
    response_model=Dict[str, Any],
    status_code=http_status.HTTP_200_OK,
    summary="Start an A/B test",
    description="Start a draft A/B test.",
)
async def start_ab_test(
    test_id: str,
    request: StartABTestRequest = None,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Start an A/B test.

    Args:
        test_id: Test identifier
        request: Start request

    Returns:
        Updated test dictionary

    Raises:
        HTTPException: If start fails
    """
    logger.info("Starting A/B test", test_id=test_id)

    try:
        service = get_ab_testing_service()
        test = service.start_test(
            test_id=test_id,
            started_by=request.started_by if request else None,
        )
        return test

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to start A/B test", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "TEST_START_ERROR",
            },
        )


@router.post(
    "/{test_id}/stop",
    response_model=Dict[str, Any],
    status_code=http_status.HTTP_200_OK,
    summary="Stop an A/B test",
    description="Stop a running A/B test and optionally declare a winner.",
)
async def stop_ab_test(
    test_id: str,
    request: StopABTestRequest,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Stop an A/B test.

    Args:
        test_id: Test identifier
        request: Stop request

    Returns:
        Updated test dictionary

    Raises:
        HTTPException: If stop fails
    """
    logger.info(
        "Stopping A/B test", test_id=test_id, winning_variant=request.winning_variant
    )

    try:
        service = get_ab_testing_service()
        test = service.stop_test(
            test_id=test_id,
            winning_variant=request.winning_variant,
            stopped_by=request.stopped_by,
        )
        return test

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to stop A/B test", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "TEST_STOP_ERROR",
            },
        )


@router.get(
    "/{test_id}/metrics",
    response_model=Dict[str, Any],
    status_code=http_status.HTTP_200_OK,
    summary="Get A/B test metrics",
    description="Retrieve metrics and analysis for an A/B test.",
)
async def get_ab_test_metrics(
    test_id: str,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Get A/B test metrics.

    Args:
        test_id: Test identifier

    Returns:
        Metrics dictionary with variant comparisons

    Raises:
        HTTPException: If metrics retrieval fails
    """
    logger.info("Getting A/B test metrics", test_id=test_id)

    try:
        service = get_ab_testing_service()
        metrics = service.get_test_metrics(test_id=test_id)
        return metrics

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to get test metrics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "METRICS_ERROR",
            },
        )


@router.post(
    "/{test_id}/assign",
    response_model=Dict[str, str],
    status_code=http_status.HTTP_200_OK,
    summary="Assign a variant",
    description="Assign an assignment key to a variant using hash-based routing.",
)
async def assign_variant(
    test_id: str,
    request: AssignVariantRequest,
    api_key: Optional[str] = Depends(get_api_key),
) -> Dict[str, str]:
    """
    Assign a variant.

    Args:
        test_id: Test identifier
        request: Assignment request

    Returns:
        Dictionary with assigned variant

    Raises:
        HTTPException: If assignment fails
    """
    logger.info(
        "Assigning variant",
        test_id=test_id,
        assignment_key=request.assignment_key,
    )

    try:
        service = get_ab_testing_service()
        variant = service.assign_variant(
            test_id=test_id,
            assignment_key=request.assignment_key,
        )
        return {"test_id": test_id, "variant": variant}

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to assign variant", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "ASSIGNMENT_ERROR",
            },
        )


@router.delete(
    "/{test_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Delete an A/B test",
    description="Delete a draft A/B test (only tests in draft status can be deleted).",
)
async def delete_ab_test(
    test_id: str,
    api_key: Optional[str] = Depends(get_api_key),
) -> None:
    """
    Delete an A/B test.

    Args:
        test_id: Test identifier

    Raises:
        HTTPException: If deletion fails
    """
    logger.info("Deleting A/B test", test_id=test_id)

    try:
        service = get_ab_testing_service()
        service.delete_test(test_id=test_id)

    except DataValidationError as e:
        logger.error("Data validation error", error=str(e))
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=e.to_dict())

    except Exception as e:
        logger.error("Failed to delete A/B test", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "TEST_DELETE_ERROR",
            },
        )
