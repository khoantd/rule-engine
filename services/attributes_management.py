"""
Attributes (Facts) Management Service with Database Integration.

This module provides services for managing Attributes/Facts, including CRUD
operations using database storage. Attributes define the data fields that can
be used when defining conditions (e.g. issue, title, age_till_now).
"""

from typing import Any, Dict, List, Optional

from common.logger import get_logger
from common.exceptions import DataValidationError, ConfigurationError
from common.repository.db_repository import AttributeRepository
from common.db_models import Attribute, RuleStatus
from common.db_connection import get_db_session

logger = get_logger(__name__)

# Allowed data types for attribute validation
ATTRIBUTE_DATA_TYPES = ("string", "number", "integer", "boolean", "date", "array", "object")


class AttributesManagementService:
    """
    Service for managing Attributes (facts) using database storage.

    This service provides CRUD operations for Attributes, which define the
    data fields that can be referenced when defining conditions.
    """

    def __init__(self, attribute_repository: Optional[AttributeRepository] = None):
        """
        Initialize attributes management service.

        Args:
            attribute_repository: Optional attribute repository. If None, creates new instance.
        """
        self.attribute_repository = attribute_repository or AttributeRepository()
        logger.debug("AttributesManagementService initialized")

    def list_attributes(self) -> List[Dict[str, Any]]:
        """
        List all attributes.

        Returns:
            List of attribute dictionaries
        """
        logger.debug("Listing all attributes")
        try:
            attributes = self.attribute_repository.list_attributes(
                status=RuleStatus.ACTIVE.value, limit=1000
            )
            result = [self._attribute_to_dict(attr) for attr in attributes]
            logger.info("Attributes listed successfully", count=len(result))
            return result
        except Exception as e:
            logger.error("Failed to list attributes", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list attributes: {str(e)}",
                error_code="ATTRIBUTES_LIST_ERROR",
                context={"error": str(e)},
            ) from e

    def get_attribute(self, attribute_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an attribute by ID.

        Args:
            attribute_id: Attribute identifier (key used in conditions and input data)

        Returns:
            Attribute dictionary if found, None otherwise

        Raises:
            DataValidationError: If attribute_id is empty
        """
        if not attribute_id or not attribute_id.strip():
            raise DataValidationError(
                "Attribute ID cannot be empty", error_code="ATTRIBUTE_ID_EMPTY"
            )

        logger.debug("Getting attribute", attribute_id=attribute_id)
        try:
            attribute = self.attribute_repository.get_attribute_by_attribute_id(
                attribute_id
            )
            if not attribute:
                logger.warning("Attribute not found", attribute_id=attribute_id)
                return None
            logger.info("Attribute found", attribute_id=attribute_id)
            return self._attribute_to_dict(attribute)
        except Exception as e:
            logger.error(
                "Failed to get attribute",
                attribute_id=attribute_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to get attribute {attribute_id}: {str(e)}",
                error_code="ATTRIBUTE_GET_ERROR",
                context={"attribute_id": attribute_id, "error": str(e)},
            ) from e

    def create_attribute(self, attribute_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new attribute.

        Args:
            attribute_data: Attribute data dictionary. Must include:
                - attribute_id: Unique identifier (key used in conditions)
                - name: Display name
                - data_type: One of string, number, integer, boolean, date, array, object

        Returns:
            Created attribute dictionary

        Raises:
            DataValidationError: If attribute data is invalid or attribute ID already exists
            ConfigurationError: If attribute cannot be created
        """
        logger.debug(
            "Creating attribute", attribute_id=attribute_data.get("attribute_id")
        )

        required_fields = ["attribute_id", "name"]
        for field in required_fields:
            if field not in attribute_data:
                raise DataValidationError(
                    f"Missing required field: {field}",
                    error_code="ATTRIBUTE_FIELD_MISSING",
                    context={"field": field},
                )

        attribute_id = attribute_data["attribute_id"]
        if not attribute_id or not attribute_id.strip():
            raise DataValidationError(
                "Attribute ID cannot be empty", error_code="ATTRIBUTE_ID_EMPTY"
            )

        data_type = attribute_data.get("data_type", "string")
        if data_type not in ATTRIBUTE_DATA_TYPES:
            raise DataValidationError(
                f"data_type must be one of: {ATTRIBUTE_DATA_TYPES}",
                error_code="ATTRIBUTE_INVALID_DATA_TYPE",
                context={"data_type": data_type},
            )

        try:
            existing = self.get_attribute(attribute_id)
            if existing:
                raise DataValidationError(
                    f"Attribute with ID '{attribute_id}' already exists",
                    error_code="ATTRIBUTE_ID_EXISTS",
                    context={"attribute_id": attribute_id},
                )

            attribute = self.attribute_repository.create_attribute(
                attribute_id=attribute_id,
                name=attribute_data.get("name", ""),
                data_type=data_type,
                description=attribute_data.get("description"),
                status=RuleStatus.ACTIVE.value,
                created_by=attribute_data.get("created_by"),
            )
            logger.info("Attribute created successfully", attribute_id=attribute_id)
            return self._attribute_to_dict(attribute)
        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create attribute",
                attribute_id=attribute_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to create attribute: {str(e)}",
                error_code="ATTRIBUTE_CREATE_ERROR",
                context={"attribute_id": attribute_id, "error": str(e)},
            ) from e

    def update_attribute(
        self, attribute_id: str, attribute_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing attribute.

        Args:
            attribute_id: Attribute identifier
            attribute_data: Updated attribute data dictionary

        Returns:
            Updated attribute dictionary

        Raises:
            DataValidationError: If attribute_id is empty or attribute not found
            ConfigurationError: If attribute cannot be updated
        """
        if not attribute_id or not attribute_id.strip():
            raise DataValidationError(
                "Attribute ID cannot be empty", error_code="ATTRIBUTE_ID_EMPTY"
            )

        if "data_type" in attribute_data:
            data_type = attribute_data["data_type"]
            if data_type not in ATTRIBUTE_DATA_TYPES:
                raise DataValidationError(
                    f"data_type must be one of: {ATTRIBUTE_DATA_TYPES}",
                    error_code="ATTRIBUTE_INVALID_DATA_TYPE",
                    context={"data_type": data_type},
                )

        logger.debug("Updating attribute", attribute_id=attribute_id)
        try:
            attribute = self.attribute_repository.get_attribute_by_attribute_id(
                attribute_id
            )
            if not attribute:
                raise DataValidationError(
                    f"Attribute with ID '{attribute_id}' not found",
                    error_code="ATTRIBUTE_NOT_FOUND",
                    context={"attribute_id": attribute_id},
                )

            with get_db_session() as session:
                # Re-attach and update
                attr = (
                    session.query(Attribute)
                    .filter(Attribute.attribute_id == attribute_id)
                    .first()
                )
                if not attr:
                    raise DataValidationError(
                        f"Attribute with ID '{attribute_id}' not found",
                        error_code="ATTRIBUTE_NOT_FOUND",
                        context={"attribute_id": attribute_id},
                    )
                if "name" in attribute_data:
                    attr.name = attribute_data["name"]
                if "description" in attribute_data:
                    attr.description = attribute_data["description"]
                if "data_type" in attribute_data:
                    attr.data_type = attribute_data["data_type"]
                if "status" in attribute_data:
                    attr.status = attribute_data["status"]
                session.flush()
                logger.info("Attribute updated successfully", attribute_id=attribute_id)
                return self._attribute_to_dict(attr)
        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update attribute",
                attribute_id=attribute_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to update attribute: {str(e)}",
                error_code="ATTRIBUTE_UPDATE_ERROR",
                context={"attribute_id": attribute_id, "error": str(e)},
            ) from e

    def delete_attribute(self, attribute_id: str) -> None:
        """
        Delete an attribute.

        Args:
            attribute_id: Attribute identifier

        Raises:
            DataValidationError: If attribute_id is empty or attribute not found
            ConfigurationError: If attribute cannot be deleted
        """
        if not attribute_id or not attribute_id.strip():
            raise DataValidationError(
                "Attribute ID cannot be empty", error_code="ATTRIBUTE_ID_EMPTY"
            )

        logger.debug("Deleting attribute", attribute_id=attribute_id)
        try:
            attribute = self.attribute_repository.get_attribute_by_attribute_id(
                attribute_id
            )
            if not attribute:
                raise DataValidationError(
                    f"Attribute with ID '{attribute_id}' not found",
                    error_code="ATTRIBUTE_NOT_FOUND",
                    context={"attribute_id": attribute_id},
                )

            self.attribute_repository.delete_attribute(attribute.id)
            logger.info("Attribute deleted successfully", attribute_id=attribute_id)
        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete attribute",
                attribute_id=attribute_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to delete attribute: {str(e)}",
                error_code="ATTRIBUTE_DELETE_ERROR",
                context={"attribute_id": attribute_id, "error": str(e)},
            ) from e

    def _attribute_to_dict(self, attribute: Attribute) -> Dict[str, Any]:
        """
        Convert Attribute model to dictionary format expected by API.

        Args:
            attribute: Attribute model instance

        Returns:
            Dictionary in API format
        """
        return {
            "id": attribute.id,
            "attribute_id": attribute.attribute_id,
            "name": attribute.name,
            "description": attribute.description,
            "data_type": attribute.data_type,
            "status": attribute.status,
            "created_at": (
                attribute.created_at.isoformat() if attribute.created_at else None
            ),
            "updated_at": (
                attribute.updated_at.isoformat() if attribute.updated_at else None
            ),
        }


_attributes_management_service: Optional[AttributesManagementService] = None


def get_attributes_management_service() -> AttributesManagementService:
    """
    Get global attributes management service instance.

    Returns:
        AttributesManagementService instance
    """
    global _attributes_management_service
    if _attributes_management_service is None:
        _attributes_management_service = AttributesManagementService()
    return _attributes_management_service
