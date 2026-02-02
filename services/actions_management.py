"""
Actions Management Service with Database Integration.

This module provides services for managing Actions and actionset entries (stored as
Pattern), including CRUD operations using database storage.
"""

from typing import Any, Dict, Optional

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.db_repository import RulesetRepository
from common.db_models import Pattern, Ruleset, RuleStatus
from common.db_connection import get_db_session
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class ActionsManagementService:
    """
    Service for managing Actions and actionset entries using database storage.

    Actionset entries are stored as Pattern rows. Each entry maps an actionset key
    (e.g., "YYY", "Y--") to an action recommendation.
    """

    def __init__(self, ruleset_repository: Optional[RulesetRepository] = None):
        """
        Initialize actions management service.

        Args:
            ruleset_repository: Optional ruleset repository. If None, creates new instance.
        """
        self.ruleset_repository = ruleset_repository or RulesetRepository()
        logger.debug("ActionsManagementService initialized")

    def _get_default_ruleset_id(self) -> int:
        """
        Get or create default ruleset ID.

        Prefers the ruleset marked as default (is_default=True), e.g. seeded
        "sample_ruleset", so actionset entries are found. Falls back to ruleset
        named "default", then creates "default" if none exists.

        Returns:
            Default ruleset ID

        Raises:
            ConfigurationError: If default ruleset cannot be found or created
        """
        try:
            # Prefer ruleset with is_default=True (e.g. seeded sample_ruleset with actionset)
            ruleset = self.ruleset_repository.get_default_ruleset()

            if not ruleset:
                ruleset = self.ruleset_repository.get_ruleset_by_name("default")

            if not ruleset:
                logger.info("Creating default ruleset for actionset")
                ruleset = self.ruleset_repository.create_ruleset(
                    name="default",
                    description="Default ruleset",
                    version="1.0",
                    is_default=True,
                )

            return ruleset.id
        except Exception as e:
            logger.error("Failed to get default ruleset", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to get default ruleset: {str(e)}",
                error_code="DEFAULT_RULESET_ERROR",
                context={"error": str(e)},
            ) from e

    def list_actions(self) -> Dict[str, Any]:
        """
        List all actionset entries (actions by actionset key).

        Returns:
            Dictionary mapping actionset keys (pattern_key) to action recommendations
        """
        logger.debug("Listing all actions")
        try:
            with get_db_session() as session:
                # Get default ruleset
                ruleset_id = self._get_default_ruleset_id()

                # Query all actionset entries (Pattern) for default ruleset
                patterns = (
                    session.query(Pattern)
                    .filter(Pattern.ruleset_id == ruleset_id)
                    .all()
                )

                # Convert to dictionary format
                result = {
                    pattern.pattern_key: pattern.action_recommendation
                    for pattern in patterns
                }

                logger.info("Actions listed successfully", count=len(result))
                return result
        except Exception as e:
            logger.error("Failed to list actions", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list actions: {str(e)}",
                error_code="ACTIONS_LIST_ERROR",
                context={"error": str(e)},
            ) from e

    def get_action(self, pattern: str) -> Optional[str]:
        """
        Get an action by actionset key.

        Args:
            pattern: Actionset key (pattern string, e.g., "YYY", "Y--")

        Returns:
            Action recommendation if found, None otherwise

        Raises:
            DataValidationError: If pattern is empty
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty", error_code="PATTERN_EMPTY"
            )

        logger.debug("Getting action", pattern=pattern)
        try:
            with get_db_session() as session:
                # Get default ruleset
                ruleset_id = self._get_default_ruleset_id()

                # Query actionset entry (Pattern)
                pattern_obj = (
                    session.query(Pattern)
                    .filter(
                        Pattern.ruleset_id == ruleset_id, Pattern.pattern_key == pattern
                    )
                    .first()
                )

                if pattern_obj:
                    logger.info("Action found", pattern=pattern)
                    return pattern_obj.action_recommendation

                logger.warning("Action not found", pattern=pattern)
                return None
        except Exception as e:
            logger.error(
                "Failed to get action", pattern=pattern, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to get action {pattern}: {str(e)}",
                error_code="ACTION_GET_ERROR",
                context={"pattern": pattern, "error": str(e)},
            ) from e

    def create_action(self, pattern: str, message: str) -> Dict[str, str]:
        """
        Create a new actionset entry.

        Args:
            pattern: Actionset key (pattern string, e.g., "YYY", "Y--")
            message: Action recommendation message

        Returns:
            Created action dictionary with pattern and message

        Raises:
            DataValidationError: If pattern or message is empty, or pattern already exists
            ConfigurationError: If action cannot be created
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty", error_code="PATTERN_EMPTY"
            )

        if not message or not message.strip():
            raise DataValidationError(
                "Message cannot be empty", error_code="MESSAGE_EMPTY"
            )

        logger.debug("Creating action", pattern=pattern)

        try:
            # Check if action already exists
            existing_action = self.get_action(pattern)
            if existing_action:
                raise DataValidationError(
                    f"Action with pattern '{pattern}' already exists",
                    error_code="PATTERN_EXISTS",
                    context={"pattern": pattern},
                )

            # Create actionset entry (Pattern) in database
            with get_db_session() as session:
                ruleset_id = self._get_default_ruleset_id()

                pattern_obj = Pattern(
                    pattern_key=pattern,
                    action_recommendation=message,
                    description=f"Actionset entry {pattern} maps to action: {message}",
                    ruleset_id=ruleset_id,
                )

                session.add(pattern_obj)
                session.flush()

                logger.info("Action created successfully", pattern=pattern)
                return {pattern: message}

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create action", pattern=pattern, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to create action: {str(e)}",
                error_code="ACTION_CREATE_ERROR",
                context={"pattern": pattern, "error": str(e)},
            ) from e

    def update_action(self, pattern: str, message: str) -> Dict[str, str]:
        """
        Update an existing actionset entry.

        Args:
            pattern: Actionset key (pattern string)
            message: Updated action recommendation message

        Returns:
            Updated action dictionary with pattern and message

        Raises:
            DataValidationError: If pattern is empty, message is empty, or pattern not found
            ConfigurationError: If action cannot be updated
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty", error_code="PATTERN_EMPTY"
            )

        if not message or not message.strip():
            raise DataValidationError(
                "Message cannot be empty", error_code="MESSAGE_EMPTY"
            )

        logger.debug("Updating action", pattern=pattern)

        try:
            with get_db_session() as session:
                # Get default ruleset
                ruleset_id = self._get_default_ruleset_id()

                # Check if actionset entry exists
                pattern_obj = (
                    session.query(Pattern)
                    .filter(
                        Pattern.ruleset_id == ruleset_id, Pattern.pattern_key == pattern
                    )
                    .first()
                )

                if not pattern_obj:
                    raise DataValidationError(
                        f"Action with pattern '{pattern}' not found",
                        error_code="PATTERN_NOT_FOUND",
                        context={"pattern": pattern},
                    )

                # Update actionset entry
                pattern_obj.action_recommendation = message
                pattern_obj.description = f"Actionset entry {pattern} maps to action: {message}"

                session.flush()

                logger.info("Action updated successfully", pattern=pattern)
                return {pattern: message}

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update action", pattern=pattern, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to update action: {str(e)}",
                error_code="ACTION_UPDATE_ERROR",
                context={"pattern": pattern, "error": str(e)},
            ) from e

    def delete_action(self, pattern: str) -> None:
        """
        Delete an actionset entry.

        Args:
            pattern: Actionset key (pattern string)

        Raises:
            DataValidationError: If pattern is empty or pattern not found
            ConfigurationError: If action cannot be deleted
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty", error_code="PATTERN_EMPTY"
            )

        logger.debug("Deleting action", pattern=pattern)

        try:
            with get_db_session() as session:
                # Get default ruleset
                ruleset_id = self._get_default_ruleset_id()

                # Check if actionset entry exists
                pattern_obj = (
                    session.query(Pattern)
                    .filter(
                        Pattern.ruleset_id == ruleset_id, Pattern.pattern_key == pattern
                    )
                    .first()
                )

                if not pattern_obj:
                    raise DataValidationError(
                        f"Action with pattern '{pattern}' not found",
                        error_code="PATTERN_NOT_FOUND",
                        context={"pattern": pattern},
                    )

                # Delete actionset entry
                session.delete(pattern_obj)

                logger.info("Action deleted successfully", pattern=pattern)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete action", pattern=pattern, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to delete action: {str(e)}",
                error_code="ACTION_DELETE_ERROR",
                context={"pattern": pattern, "error": str(e)},
            ) from e


# Global service instance
_actions_management_service: Optional[ActionsManagementService] = None


def get_actions_management_service() -> ActionsManagementService:
    """
    Get global actions management service instance.

    Returns:
        ActionsManagementService instance
    """
    global _actions_management_service
    if _actions_management_service is None:
        _actions_management_service = ActionsManagementService()
    return _actions_management_service
