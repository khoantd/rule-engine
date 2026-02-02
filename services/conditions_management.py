"""
Conditions Management Service with Database Integration.

This module provides services for managing Conditions, including CRUD operations
using database storage.
"""

from typing import Any, Dict, List, Optional

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.db_repository import ConditionRepository
from common.db_models import Condition, RuleStatus
from common.db_connection import get_db_session
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class ConditionsManagementService:
    """
    Service for managing Conditions using database storage.

    This service provides CRUD operations for Conditions, using database
    for persistence.
    """

    def __init__(self, condition_repository: Optional[ConditionRepository] = None):
        """
        Initialize conditions management service.

        Args:
            condition_repository: Optional condition repository. If None, creates new instance.
        """
        self.condition_repository = condition_repository or ConditionRepository()
        logger.debug("ConditionsManagementService initialized")

    def list_conditions(self) -> List[Dict[str, Any]]:
        """
        List all conditions.

        Returns:
            List of condition dictionaries
        """
        logger.debug("Listing all conditions")
        try:
            conditions = self.condition_repository.list_conditions(
                status=RuleStatus.ACTIVE.value, limit=1000
            )

            result = [self._condition_to_dict(condition) for condition in conditions]
            logger.info("Conditions listed successfully", count=len(result))
            return result
        except Exception as e:
            logger.error("Failed to list conditions", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list conditions: {str(e)}",
                error_code="CONDITIONS_LIST_ERROR",
                context={"error": str(e)},
            ) from e

    def get_condition(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a condition by ID.

        Args:
            condition_id: Condition identifier

        Returns:
            Condition dictionary if found, None otherwise

        Raises:
            DataValidationError: If condition_id is empty
        """
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty", error_code="CONDITION_ID_EMPTY"
            )

        logger.debug("Getting condition", condition_id=condition_id)
        try:
            with get_db_session() as session:
                condition = (
                    session.query(Condition)
                    .filter(Condition.condition_id == condition_id)
                    .first()
                )

                if not condition:
                    logger.warning("Condition not found", condition_id=condition_id)
                    return None

                logger.info("Condition found", condition_id=condition_id)
                return self._condition_to_dict(condition)
        except Exception as e:
            logger.error(
                "Failed to get condition",
                condition_id=condition_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to get condition {condition_id}: {str(e)}",
                error_code="CONDITION_GET_ERROR",
                context={"condition_id": condition_id, "error": str(e)},
            ) from e

    def create_condition(self, condition_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new condition.

        Args:
            condition_data: Condition data dictionary. Must include:
                - condition_id: Unique condition identifier
                - condition_name: Condition name
                - attribute: Attribute name to check
                - equation: Equation operator
                - constant: Comparison value

        Returns:
            Created condition dictionary

        Raises:
            DataValidationError: If condition data is invalid or condition ID already exists
            ConfigurationError: If condition cannot be created
        """
        logger.debug(
            "Creating condition", condition_id=condition_data.get("condition_id")
        )

        # Validate required fields
        required_fields = [
            "condition_id",
            "condition_name",
            "attribute",
            "equation",
            "constant",
        ]
        for field in required_fields:
            if field not in condition_data:
                raise DataValidationError(
                    f"Missing required field: {field}",
                    error_code="CONDITION_FIELD_MISSING",
                    context={"field": field},
                )

        condition_id = condition_data["condition_id"]
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty", error_code="CONDITION_ID_EMPTY"
            )

        try:
            # Check if condition already exists
            existing_condition = self.get_condition(condition_id)
            if existing_condition:
                raise DataValidationError(
                    f"Condition with ID '{condition_id}' already exists",
                    error_code="CONDITION_ID_EXISTS",
                    context={"condition_id": condition_id},
                )

            # Create condition in database
            condition = self.condition_repository.create_condition(
                condition_id=condition_id,
                name=condition_data.get("condition_name", ""),
                description=condition_data.get("description"),
                attribute=condition_data.get("attribute", ""),
                operator=condition_data.get(
                    "equation", condition_data.get("operator", "equal")
                ),
                value=str(condition_data.get("constant", "")),
                status=RuleStatus.ACTIVE.value,
                created_by=condition_data.get("created_by"),
            )

            logger.info("Condition created successfully", condition_id=condition_id)
            return self._condition_to_dict(condition)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create condition",
                condition_id=condition_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to create condition: {str(e)}",
                error_code="CONDITION_CREATE_ERROR",
                context={"condition_id": condition_id, "error": str(e)},
            ) from e

    def update_condition(
        self, condition_id: str, condition_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing condition.

        Args:
            condition_id: Condition identifier
            condition_data: Updated condition data dictionary

        Returns:
            Updated condition dictionary

        Raises:
            DataValidationError: If condition_id is empty or condition not found
            ConfigurationError: If condition cannot be updated
        """
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty", error_code="CONDITION_ID_EMPTY"
            )

        logger.debug("Updating condition", condition_id=condition_id)

        try:
            # Get existing condition
            with get_db_session() as session:
                condition = (
                    session.query(Condition)
                    .filter(Condition.condition_id == condition_id)
                    .first()
                )

                if not condition:
                    raise DataValidationError(
                        f"Condition with ID '{condition_id}' not found",
                        error_code="CONDITION_NOT_FOUND",
                        context={"condition_id": condition_id},
                    )

                # Prepare update data
                if "condition_name" in condition_data:
                    condition.name = condition_data["condition_name"]
                if "description" in condition_data:
                    condition.description = condition_data["description"]
                if "attribute" in condition_data:
                    condition.attribute = condition_data["attribute"]
                if "equation" in condition_data:
                    condition.operator = condition_data["equation"]
                elif "operator" in condition_data:
                    condition.operator = condition_data["operator"]
                if "constant" in condition_data:
                    condition.value = str(condition_data["constant"])
                if "status" in condition_data:
                    condition.status = condition_data["status"]

                session.flush()

                logger.info("Condition updated successfully", condition_id=condition_id)
                return self._condition_to_dict(condition)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update condition",
                condition_id=condition_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to update condition: {str(e)}",
                error_code="CONDITION_UPDATE_ERROR",
                context={"condition_id": condition_id, "error": str(e)},
            ) from e

    def delete_condition(self, condition_id: str) -> None:
        """
        Delete a condition.

        Args:
            condition_id: Condition identifier

        Raises:
            DataValidationError: If condition_id is empty or condition not found
            ConfigurationError: If condition cannot be deleted
        """
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty", error_code="CONDITION_ID_EMPTY"
            )

        logger.debug("Deleting condition", condition_id=condition_id)

        try:
            # Get existing condition
            with get_db_session() as session:
                condition = (
                    session.query(Condition)
                    .filter(Condition.condition_id == condition_id)
                    .first()
                )

                if not condition:
                    raise DataValidationError(
                        f"Condition with ID '{condition_id}' not found",
                        error_code="CONDITION_NOT_FOUND",
                        context={"condition_id": condition_id},
                    )

                # Delete condition
                session.delete(condition)

                logger.info("Condition deleted successfully", condition_id=condition_id)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete condition",
                condition_id=condition_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to delete condition: {str(e)}",
                error_code="CONDITION_DELETE_ERROR",
                context={"condition_id": condition_id, "error": str(e)},
            ) from e

    def _condition_to_dict(self, condition: Condition) -> Dict[str, Any]:
        """
        Convert Condition model to dictionary format expected by API.

        Args:
            condition: Condition model instance

        Returns:
            Dictionary in rule engine format
        """
        return {
            "id": condition.id,
            "condition_id": condition.condition_id,
            "name": condition.name,
            "condition_name": condition.name,
            "description": condition.description,
            "attribute": condition.attribute,
            "equation": condition.operator,
            "operator": condition.operator,
            "constant": condition.value,
            "value": condition.value,
            "status": condition.status,
            "created_at": condition.created_at.isoformat()
            if condition.created_at
            else None,
            "updated_at": condition.updated_at.isoformat()
            if condition.updated_at
            else None,
        }


# Global service instance
_conditions_management_service: Optional[ConditionsManagementService] = None


def get_conditions_management_service() -> ConditionsManagementService:
    """
    Get global conditions management service instance.

    Returns:
        ConditionsManagementService instance
    """
    global _conditions_management_service
    if _conditions_management_service is None:
        _conditions_management_service = ConditionsManagementService()
    return _conditions_management_service
