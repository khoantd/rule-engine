"""
API routes for Attributes (facts) management (CRUD operations).

This module provides REST API endpoints for managing Attributes/Facts, which
define the data fields that can be used when defining conditions.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request

from api.models import (
    AttributeCreateRequest,
    AttributeUpdateRequest,
    AttributeResponse,
    AttributesListResponse,
    ErrorResponse,
)
from services.attributes_management import get_attributes_management_service
from common.logger import get_logger
from common.exceptions import DataValidationError, ConfigurationError
from api.middleware.auth import get_api_key

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
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> AttributesListResponse:
    """
    List all attributes (facts).

    Returns:
        List of all attributes in the system

    Raises:
        HTTPException: If listing fails
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)

    logger.info("API list attributes request", correlation_id=correlation_id)

    try:
        service = get_attributes_management_service()
        attributes_data = service.list_attributes()

        attributes = [AttributeResponse(**attr) for attr in attributes_data]

        logger.info(
            "API list attributes completed",
            correlation_id=correlation_id,
            count=len(attributes),
        )

        return AttributesListResponse(attributes=attributes, count=len(attributes))

    except ConfigurationError as e:
        logger.error(
            "Configuration error listing attributes",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )
    except Exception as e:
        logger.error(
            "Unexpected error listing attributes",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


@router.get(
    "/{attribute_id}",
    response_model=AttributeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an attribute by ID",
    description="Retrieve a specific attribute (fact) by its identifier.",
)
async def get_attribute(
    attribute_id: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> AttributeResponse:
    """
    Get an attribute by ID.

    Args:
        attribute_id: Attribute identifier (key used in conditions)

    Returns:
        Attribute details

    Raises:
        HTTPException: If attribute not found or retrieval fails
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)

    logger.info(
        "API get attribute request",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )

    try:
        service = get_attributes_management_service()
        attribute_data = service.get_attribute(attribute_id)

        if not attribute_data:
            logger.warning(
                "Attribute not found",
                correlation_id=correlation_id,
                attribute_id=attribute_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Attribute with ID '{attribute_id}' not found",
                    "error_code": "ATTRIBUTE_NOT_FOUND",
                    "context": {"attribute_id": attribute_id},
                },
            )

        logger.info(
            "API get attribute completed",
            correlation_id=correlation_id,
            attribute_id=attribute_id,
        )

        return AttributeResponse(**attribute_data)

    except DataValidationError as e:
        logger.error(
            "Data validation error getting attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error(
            "Configuration error getting attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )
    except Exception as e:
        logger.error(
            "Unexpected error getting attribute",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


@router.post(
    "",
    response_model=AttributeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new attribute",
    description="Create a new attribute (fact) for use in condition definitions.",
)
async def create_attribute(
    request: AttributeCreateRequest,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> AttributeResponse:
    """
    Create a new attribute (fact).

    Args:
        request: Attribute creation request

    Returns:
        Created attribute details

    Raises:
        HTTPException: If creation fails or validation fails
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)

    logger.info(
        "API create attribute request",
        correlation_id=correlation_id,
        attribute_id=request.attribute_id,
    )

    try:
        service = get_attributes_management_service()

        attribute_data = request.dict(exclude_none=False)
        created_attribute = service.create_attribute(attribute_data)

        logger.info(
            "API create attribute completed",
            correlation_id=correlation_id,
            attribute_id=request.attribute_id,
        )

        return AttributeResponse(**created_attribute)

    except DataValidationError as e:
        logger.error(
            "Data validation error creating attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )
    except ConfigurationError as e:
        logger.error(
            "Configuration error creating attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )
    except Exception as e:
        logger.error(
            "Unexpected error creating attribute",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


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
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> AttributeResponse:
    """
    Update an existing attribute.

    Args:
        attribute_id: Attribute identifier
        request: Attribute update request

    Returns:
        Updated attribute details

    Raises:
        HTTPException: If update fails, attribute not found, or validation fails
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)

    logger.info(
        "API update attribute request",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )

    try:
        service = get_attributes_management_service()

        existing_attribute = service.get_attribute(attribute_id)
        if not existing_attribute:
            logger.warning(
                "Attribute not found for update",
                correlation_id=correlation_id,
                attribute_id=attribute_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_type": "NotFoundError",
                    "message": f"Attribute with ID '{attribute_id}' not found",
                    "error_code": "ATTRIBUTE_NOT_FOUND",
                    "context": {"attribute_id": attribute_id},
                },
            )

        attribute_data = existing_attribute.copy()
        update_data = request.dict(exclude_none=True)
        attribute_data.update(update_data)

        updated_attribute = service.update_attribute(attribute_id, attribute_data)

        logger.info(
            "API update attribute completed",
            correlation_id=correlation_id,
            attribute_id=attribute_id,
        )

        return AttributeResponse(**updated_attribute)

    except DataValidationError as e:
        logger.error(
            "Data validation error updating attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )
    except HTTPException:
        raise
    except ConfigurationError as e:
        logger.error(
            "Configuration error updating attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating attribute",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR",
            },
        )


@router.delete(
    "/{attribute_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an attribute",
    description="Delete an attribute by its identifier.",
)
async def delete_attribute(
    attribute_id: str,
    http_request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> None:
    """
    Delete an attribute.

    Args:
        attribute_id: Attribute identifier

    Raises:
        HTTPException: If deletion fails or attribute not found
    """
    correlation_id = getattr(http_request.state, "correlation_id", None)

    logger.info(
        "API delete attribute request",
        correlation_id=correlation_id,
        attribute_id=attribute_id,
    )

    try:
        service = get_attributes_management_service()
        service.delete_attribute(attribute_id)

        logger.info(
            "API delete attribute completed",
            correlation_id=correlation_id,
            attribute_id=attribute_id,
        )

    except DataValidationError as e:
        logger.error(
            "Data validation error deleting attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )
    except ConfigurationError as e:
        logger.error(
            "Configuration error deleting attribute",
            error=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )
    except Exception as e:
        logger.error(
            "Unexpected error deleting attribute",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": type(e).__name__,
                "message": str(e),
                "error_code": "UNEXPECTED_ERROR",
            },
        )
