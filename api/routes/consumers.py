"""
Consumer Management API Routes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.models import (
    ConsumerCreateRequest,
    ConsumerUpdateRequest,
    ConsumerResponse,
    ConsumersListResponse,
    ErrorResponse,
)
from services.consumer_management import (
    ConsumerManagementService,
    get_consumer_management_service,
)
from common.exceptions import DataValidationError, ConfigurationError
from common.logger import get_logger

router = APIRouter(prefix="/consumers", tags=["Consumer Management"])
logger = get_logger(__name__)


@router.get("", response_model=ConsumersListResponse)
async def list_consumers(
    status: Optional[str] = Query(None, description="Filter by status (active, inactive)"),
    service: ConsumerManagementService = Depends(get_consumer_management_service),
):
    """List all consumers."""
    try:
        consumers = service.list_consumers(status=status)
        return {"consumers": consumers, "count": len(consumers)}
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{consumer_id}", response_model=ConsumerResponse)
async def get_consumer(
    consumer_id: str,
    service: ConsumerManagementService = Depends(get_consumer_management_service),
):
    """Get a consumer by ID."""
    consumer = service.get_consumer(consumer_id)
    if not consumer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumer '{consumer_id}' not found",
        )
    return consumer


@router.post(
    "",
    response_model=ConsumerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def create_consumer(
    request: ConsumerCreateRequest,
    service: ConsumerManagementService = Depends(get_consumer_management_service),
):
    """Create a new consumer."""
    try:
        return service.create_consumer(request.dict())
    except DataValidationError as e:
        if e.error_code == "CONSUMER_ALREADY_EXISTS":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error in create_consumer route", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{consumer_id}", response_model=ConsumerResponse)
async def update_consumer(
    consumer_id: str,
    request: ConsumerUpdateRequest,
    service: ConsumerManagementService = Depends(get_consumer_management_service),
):
    """Update a consumer."""
    try:
        return service.update_consumer(consumer_id, request.dict(exclude_unset=True))
    except DataValidationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating consumer: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{consumer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consumer(
    consumer_id: str,
    service: ConsumerManagementService = Depends(get_consumer_management_service),
):
    """Delete a consumer."""
    try:
        service.delete_consumer(consumer_id)
    except DataValidationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting consumer: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
