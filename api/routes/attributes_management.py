"""
API routes for Attributes (facts) management (CRUD operations).

Domain exceptions propagate to ``api.middleware.errors``.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status

from api.deps import get_attributes_management_service_dep, get_correlation_id
from api.middleware.auth import get_api_key
from api.models import (
    AttributeCreateRequest,
    AttributeResponse,
    AttributesListResponse,
    AttributeUpdateRequest,
    ErrorResponse,
)
from common.exceptions import NotFoundError
from common.logger import get_logger
from services.attributes_management import AttributesManagementService

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/management/attributes",
    tags=["attributes-management"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)


@router.get(
    "",
    response_model=AttributesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all attributes",
    description="Retrieve a list of all configured attributes (facts) for use in conditions.",
)
async def list_attributes(
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: AttributesManagementService = Depends(get_attributes_management_service_dep),
) -> AttributesListResponse:
    """List all attributes (facts)."""
    logger.info("API list attributes request", correlation_id=correlation_id)
    attributes_data = service.list_attributes()
    attributes = [AttributeResponse(**attr) for attr in attributes_data]
    logger.info(
        "API list attributes completed",
        correlation_id=correlation_id,
        count=len(attributes),
    )
    return AttributesListResponse(attributes=attributes, count=len(attributes))


@router.get(
    "/{attribute_id}",
    response_model=AttributeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an attribute by ID",
    description="Retrieve a specific attribute (fact) by its identifier.",
)
async def get_attribute(
    attribute_id: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: AttributesManagementService = Depends(get_attributes_management_service_dep),
) -> AttributeResponse:
    """Get an attribute by ID."""
    logger.info(
        "API get attribute request",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )
    attribute_data = service.get_attribute(attribute_id)
    if not attribute_data:
        logger.warning(
            "Attribute not found",
            correlation_id=correlation_id,
            attribute_id=attribute_id,
        )
        raise NotFoundError(
            f"Attribute with ID '{attribute_id}' not found",
            error_code="ATTRIBUTE_NOT_FOUND",
            context={"attribute_id": attribute_id},
        )
    logger.info(
        "API get attribute completed",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )
    return AttributeResponse(**attribute_data)


@router.post(
    "",
    response_model=AttributeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new attribute",
    description="Create a new attribute (fact) for use in condition definitions.",
)
async def create_attribute(
    request: AttributeCreateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: AttributesManagementService = Depends(get_attributes_management_service_dep),
) -> AttributeResponse:
    """Create a new attribute (fact)."""
    logger.info(
        "API create attribute request",
        correlation_id=correlation_id,
        attribute_id=request.attribute_id,
    )
    attribute_data = request.model_dump(exclude_none=False)
    created_attribute = service.create_attribute(attribute_data)
    logger.info(
        "API create attribute completed",
        correlation_id=correlation_id,
        attribute_id=request.attribute_id,
    )
    return AttributeResponse(**created_attribute)


@router.put(
    "/{attribute_id}",
    response_model=AttributeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing attribute",
    description="Update an existing attribute with new configuration.",
)
async def update_attribute(
    attribute_id: str,
    request: AttributeUpdateRequest,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: AttributesManagementService = Depends(get_attributes_management_service_dep),
) -> AttributeResponse:
    """Update an existing attribute."""
    logger.info(
        "API update attribute request",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )
    existing_attribute = service.get_attribute(attribute_id)
    if not existing_attribute:
        logger.warning(
            "Attribute not found for update",
            correlation_id=correlation_id,
            attribute_id=attribute_id,
        )
        raise NotFoundError(
            f"Attribute with ID '{attribute_id}' not found",
            error_code="ATTRIBUTE_NOT_FOUND",
            context={"attribute_id": attribute_id},
        )
    attribute_data = existing_attribute.copy()
    attribute_data.update(request.model_dump(exclude_none=True))
    updated_attribute = service.update_attribute(attribute_id, attribute_data)
    logger.info(
        "API update attribute completed",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )
    return AttributeResponse(**updated_attribute)


@router.delete(
    "/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute",
    description="Delete an attribute by its identifier.",
)
async def delete_attribute(
    attribute_id: str,
    correlation_id: Optional[str] = Depends(get_correlation_id),
    api_key: Optional[str] = Depends(get_api_key),
    service: AttributesManagementService = Depends(get_attributes_management_service_dep),
) -> None:
    """Delete an attribute."""
    logger.info(
        "API delete attribute request",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )
    service.delete_attribute(attribute_id)
    logger.info(
        "API delete attribute completed",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )
