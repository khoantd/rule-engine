"""
Consumer Management API Routes.

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from api.deps import get_consumer_management_service_dep
from api.models import (
    ConsumerCreateRequest,
    ConsumerResponse,
    ConsumersListResponse,
    ConsumerUpdateRequest,
    ErrorResponse,
)
from common.exceptions import NotFoundError
from services.consumer_management import ConsumerManagementService

router = APIRouter(prefix="/consumers", tags=["Consumer Management"])


@router.get("", response_model=ConsumersListResponse)
async def list_consumers(
    status: Optional[str] = Query(None, description="Filter by status (active, inactive)"),
    service: ConsumerManagementService = Depends(get_consumer_management_service_dep),
) -> ConsumersListResponse:
    """List all consumers."""
    rows = service.list_consumers(status=status)
    consumers = [ConsumerResponse(**c) for c in rows]
    return ConsumersListResponse(consumers=consumers, count=len(consumers))


@router.get("/{consumer_id}", response_model=ConsumerResponse)
async def get_consumer(
    consumer_id: str,
    service: ConsumerManagementService = Depends(get_consumer_management_service_dep),
) -> ConsumerResponse:
    """Get a consumer by ID."""
    consumer = service.get_consumer(consumer_id)
    if not consumer:
        raise NotFoundError(
            f"Consumer '{consumer_id}' not found",
            error_code="CONSUMER_NOT_FOUND",
            context={"consumer_id": consumer_id},
        )
    return ConsumerResponse(**consumer)


@router.post(
    "",
    response_model=ConsumerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def create_consumer(
    request: ConsumerCreateRequest,
    service: ConsumerManagementService = Depends(get_consumer_management_service_dep),
) -> ConsumerResponse:
    """Create a new consumer."""
    created = service.create_consumer(request.model_dump())
    return ConsumerResponse(**created)


@router.put("/{consumer_id}", response_model=ConsumerResponse)
async def update_consumer(
    consumer_id: str,
    request: ConsumerUpdateRequest,
    service: ConsumerManagementService = Depends(get_consumer_management_service_dep),
) -> ConsumerResponse:
    """Update a consumer."""
    updated = service.update_consumer(consumer_id, request.model_dump(exclude_unset=True))
    return ConsumerResponse(**updated)


@router.delete("/{consumer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consumer(
    consumer_id: str,
    service: ConsumerManagementService = Depends(get_consumer_management_service_dep),
) -> None:
    """Delete a consumer."""
    service.delete_consumer(consumer_id)
