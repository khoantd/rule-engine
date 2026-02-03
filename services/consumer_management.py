"""
Consumer Management Service.

This module provides services for managing Consumers, including CRUD operations
using database storage.
"""

from typing import Any, Dict, List, Optional

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.db_repository import ConsumerRepository
from common.db_models import Consumer, RuleStatus

logger = get_logger(__name__)


class ConsumerManagementService:
    """
    Service for managing Consumers using database storage.
    """

    def __init__(self, consumer_repository: Optional[ConsumerRepository] = None):
        """
        Initialize consumer management service.

        Args:
            consumer_repository: Optional consumer repository. If None, creates new instance.
        """
        self.consumer_repository = consumer_repository or ConsumerRepository()
        logger.debug("ConsumerManagementService initialized")

    def list_consumers(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all consumers.

        Args:
            status: Optional status filter

        Returns:
            List of consumer dictionaries
        """
        logger.debug("Listing all consumers", status=status)
        try:
            consumers = self.consumer_repository.list_consumers(status=status)
            result = [self._consumer_to_dict(c) for c in consumers]
            logger.info("Consumers listed successfully", count=len(result))
            return result
        except Exception as e:
            logger.error("Failed to list consumers", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list consumers: {str(e)}",
                error_code="CONSUMERS_LIST_ERROR",
                context={"error": str(e)},
            ) from e

    def get_consumer(self, consumer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a consumer by business ID.

        Args:
            consumer_id: Consumer identifier

        Returns:
            Consumer dictionary if found, None otherwise
        """
        if not consumer_id or not consumer_id.strip():
            raise DataValidationError("Consumer ID cannot be empty", error_code="CONSUMER_ID_EMPTY")

        logger.debug("Getting consumer", consumer_id=consumer_id)
        try:
            consumer = self.consumer_repository.get_consumer_by_consumer_id(consumer_id)
            if not consumer:
                logger.warning("Consumer not found", consumer_id=consumer_id)
                return None

            return self._consumer_to_dict(consumer)
        except Exception as e:
            logger.error("Failed to get consumer", consumer_id=consumer_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to get consumer {consumer_id}: {str(e)}",
                error_code="CONSUMER_GET_ERROR",
                context={"consumer_id": consumer_id, "error": str(e)},
            ) from e

    def create_consumer(self, consumer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new consumer.

        Args:
            consumer_data: Consumer data dictionary

        Returns:
            Created consumer dictionary
        """
        logger.debug("Creating consumer", consumer_id=consumer_data.get("consumer_id"))

        # Validate required fields
        if "consumer_id" not in consumer_data:
            raise DataValidationError("Missing required field: consumer_id", error_code="CONSUMER_ID_MISSING")
        if "name" not in consumer_data:
            raise DataValidationError("Missing required field: name", error_code="CONSUMER_NAME_MISSING")

        consumer_id = consumer_data["consumer_id"]
        
        try:
            # Check if already exists
            existing = self.consumer_repository.get_consumer_by_consumer_id(consumer_id)
            if existing:
                raise DataValidationError(
                    f"Consumer with ID '{consumer_id}' already exists",
                    error_code="CONSUMER_ALREADY_EXISTS",
                )

            logger.info("Calling repository create_consumer", consumer_id=consumer_id)
            consumer = self.consumer_repository.create_consumer(
                consumer_id=consumer_id,
                name=consumer_data["name"],
                description=consumer_data.get("description"),
                status=consumer_data.get("status", RuleStatus.ACTIVE.value),
                tags=consumer_data.get("tags"),
                metadata=consumer_data.get("metadata"),
                created_by=consumer_data.get("created_by"),
            )

            logger.info("Consumer created successfully", consumer_id=consumer_id)
            return self._consumer_to_dict(consumer)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create consumer: {str(e)}", consumer_id=consumer_id, exc_info=True)
            raise ConfigurationError(
                f"Failed to create consumer: {str(e)}",
                error_code="CONSUMER_CREATE_ERROR",
                context={"consumer_id": consumer_id},
            ) from e

    def update_consumer(self, consumer_id: str, consumer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing consumer.
        """
        logger.debug("Updating consumer", consumer_id=consumer_id)
        try:
            existing = self.consumer_repository.get_consumer_by_consumer_id(consumer_id)
            if not existing:
                raise DataValidationError(f"Consumer '{consumer_id}' not found", error_code="CONSUMER_NOT_FOUND")

            update_kwargs = {}
            if "name" in consumer_data:
                update_kwargs["name"] = consumer_data["name"]
            if "description" in consumer_data:
                update_kwargs["description"] = consumer_data["description"]
            if "status" in consumer_data:
                update_kwargs["status"] = consumer_data["status"]
            if "tags" in consumer_data:
                update_kwargs["tags"] = consumer_data["tags"]
            if "metadata" in consumer_data:
                update_kwargs["extra_metadata"] = consumer_data["metadata"]

            updated = self.consumer_repository.update_consumer(existing.id, **update_kwargs)
            logger.info("Consumer updated successfully", consumer_id=consumer_id)
            return self._consumer_to_dict(updated)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to update consumer", consumer_id=consumer_id, error=str(e), exc_info=True)
            raise ConfigurationError(f"Failed to update consumer {consumer_id}: {str(e)}", error_code="CONSUMER_UPDATE_ERROR")

    def delete_consumer(self, consumer_id: str) -> None:
        """
        Delete a consumer.
        """
        logger.debug("Deleting consumer", consumer_id=consumer_id)
        try:
            existing = self.consumer_repository.get_consumer_by_consumer_id(consumer_id)
            if not existing:
                raise DataValidationError(f"Consumer '{consumer_id}' not found", error_code="CONSUMER_NOT_FOUND")

            self.consumer_repository.delete_consumer(existing.id)
            logger.info("Consumer deleted successfully", consumer_id=consumer_id)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to delete consumer", consumer_id=consumer_id, error=str(e), exc_info=True)
            raise ConfigurationError(f"Failed to delete consumer {consumer_id}: {str(e)}", error_code="CONSUMER_DELETE_ERROR")

    def _consumer_to_dict(self, consumer: Consumer) -> Dict[str, Any]:
        """Convert Consumer model to dictionary."""
        return consumer.to_dict()


# Global service instance
_consumer_management_service: Optional[ConsumerManagementService] = None


def get_consumer_management_service() -> ConsumerManagementService:
    """Get global service instance."""
    global _consumer_management_service
    if _consumer_management_service is None:
        _consumer_management_service = ConsumerManagementService()
    return _consumer_management_service
