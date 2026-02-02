"""
Rule Management Service with Database Integration.

This module provides services for managing Rules, including CRUD operations
using database storage.
"""

from typing import Any, Dict, List, Optional

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.db_repository import RuleRepository, RulesetRepository
from common.db_models import Rule, RuleStatus
from common.db_connection import get_db_session
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class RuleManagementService:
    """
    Service for managing Rules using database storage.

    This service provides CRUD operations for Rules, using database
    for persistence.
    """

    def __init__(
        self,
        rule_repository: Optional[RuleRepository] = None,
        ruleset_repository: Optional[RulesetRepository] = None,
    ):
        """
        Initialize rule management service.

        Args:
            rule_repository: Optional rule repository. If None, creates new instance.
            ruleset_repository: Optional ruleset repository. If None, creates new instance.
        """
        self.rule_repository = rule_repository or RuleRepository()
        self.ruleset_repository = ruleset_repository or RulesetRepository()
        logger.debug("RuleManagementService initialized")

    def _get_default_ruleset_id(self) -> int:
        """
        Get or create default ruleset ID.

        Returns:
            Default ruleset ID

        Raises:
            ConfigurationError: If default ruleset cannot be found or created
        """
        try:
            ruleset = self.ruleset_repository.get_ruleset_by_name("default")

            if not ruleset:
                logger.info("Creating default ruleset")
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

    def list_rules(self, ruleset_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all rules.

        Args:
            ruleset_id: Optional ruleset ID to filter by

        Returns:
            List of rule dictionaries
        """
        logger.debug("Listing all rules", ruleset_id=ruleset_id)
        try:
            rules = self.rule_repository.list_rules(
                ruleset_id=ruleset_id, status=RuleStatus.ACTIVE.value, limit=1000
            )

            result = [self._rule_to_dict(rule) for rule in rules]
            logger.info("Rules listed successfully", count=len(result))
            return result
        except Exception as e:
            logger.error("Failed to list rules", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list rules: {str(e)}",
                error_code="RULES_LIST_ERROR",
                context={"error": str(e)},
            ) from e

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a rule by ID.

        Args:
            rule_id: Rule identifier

        Returns:
            Rule dictionary if found, None otherwise

        Raises:
            DataValidationError: If rule_id is empty
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        logger.debug("Getting rule", rule_id=rule_id)
        try:
            rule = self.rule_repository.get_rule_by_rule_id(rule_id)

            if not rule:
                logger.warning("Rule not found", rule_id=rule_id)
                return None

            logger.info("Rule found", rule_id=rule_id)
            return self._rule_to_dict(rule)
        except Exception as e:
            logger.error(
                "Failed to get rule", rule_id=rule_id, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to get rule {rule_id}: {str(e)}",
                error_code="RULE_GET_ERROR",
                context={"rule_id": rule_id, "error": str(e)},
            ) from e

    def create_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new rule.

        Args:
            rule_data: Rule data dictionary. Must include:
                - id: Unique rule identifier
                - rule_name: Rule name
                - conditions: Conditions dictionary or inline condition (attribute, equation, constant)
                - description: Rule description
                - result: Result string
                - Optional: rule_point, weight, priority, type, action_result

        Returns:
            Created rule dictionary

        Raises:
            DataValidationError: If rule data is invalid
            ConfigurationError: If rule cannot be created or updated
        """
        logger.debug("Creating rule", rule_id=rule_data.get("id"))

        # Validate required fields
        required_fields = ["id", "rule_name", "description", "result"]
        for field in required_fields:
            if field not in rule_data:
                raise DataValidationError(
                    f"Missing required field: {field}",
                    error_code="RULE_FIELD_MISSING",
                    context={"field": field},
                )

        rule_id = rule_data["id"]
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        try:
            # If rule already exists, update it (upsert semantics)
            existing_rule = self.get_rule(rule_id)
            if existing_rule:
                logger.info("Rule exists, updating", rule_id=rule_id)
                return self.update_rule(rule_id, rule_data)

            # Get ruleset ID
            ruleset_id = rule_data.get("ruleset_id")
            if ruleset_id is None:
                ruleset_id = self._get_default_ruleset_id()

            # Handle conditions - could be inline or reference
            conditions = rule_data.get("conditions", {})

            if isinstance(conditions, dict):
                # Check if it's inline conditions (has attribute, equation, constant)
                if "attribute" in conditions:
                    attribute = conditions.get("attribute", "")
                    condition = conditions.get(
                        "equation", conditions.get("condition", "equal")
                    )
                    constant = conditions.get("constant", "")
                else:
                    # Reference format - extract from first item
                    attribute = ""
                    condition = "equal"
                    constant = ""
            else:
                attribute = ""
                condition = "equal"
                constant = ""

            # Create rule in database
            rule = self.rule_repository.create_rule(
                rule_id=rule_id,
                rule_name=rule_data.get("rule_name", ""),
                attribute=attribute,
                condition=condition,
                constant=str(constant),
                ruleset_id=ruleset_id,
                message=rule_data.get("description", ""),
                weight=float(rule_data.get("weight", 1.0)),
                rule_point=int(rule_data.get("rule_point", 10)),
                priority=int(rule_data.get("priority", 0)),
                action_result=rule_data.get(
                    "result", rule_data.get("action_result", "Y")
                ),
                status=RuleStatus.ACTIVE.value,
                version=rule_data.get("version", "1.0"),
                created_by=rule_data.get("created_by"),
            )

            logger.info("Rule created successfully", rule_id=rule_id)
            return self._rule_to_dict(rule)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create rule", rule_id=rule_id, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to create rule: {str(e)}",
                error_code="RULE_CREATE_ERROR",
                context={"rule_id": rule_id, "error": str(e)},
            ) from e

    def update_rule(self, rule_id: str, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing rule.

        Args:
            rule_id: Rule identifier
            rule_data: Updated rule data dictionary

        Returns:
            Updated rule dictionary

        Raises:
            DataValidationError: If rule_id is empty or rule not found
            ConfigurationError: If rule cannot be updated
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        logger.debug("Updating rule", rule_id=rule_id)

        try:
            # Get existing rule
            existing = self.rule_repository.get_rule_by_rule_id(rule_id)
            if not existing:
                raise DataValidationError(
                    f"Rule with ID '{rule_id}' not found",
                    error_code="RULE_NOT_FOUND",
                    context={"rule_id": rule_id},
                )

            # Prepare update data
            update_kwargs = {}

            if "rule_name" in rule_data:
                update_kwargs["rule_name"] = rule_data["rule_name"]
            if "description" in rule_data:
                update_kwargs["message"] = rule_data["description"]
            if "result" in rule_data:
                update_kwargs["action_result"] = rule_data["result"]
            if "action_result" in rule_data:
                update_kwargs["action_result"] = rule_data["action_result"]
            if "weight" in rule_data:
                update_kwargs["weight"] = float(rule_data["weight"])
            if "rule_point" in rule_data:
                update_kwargs["rule_point"] = int(rule_data["rule_point"])
            if "priority" in rule_data:
                update_kwargs["priority"] = int(rule_data["priority"])
            if "status" in rule_data:
                update_kwargs["status"] = rule_data["status"]
            if "version" in rule_data:
                update_kwargs["version"] = rule_data["version"]

            # Handle conditions
            conditions = rule_data.get("conditions")
            if conditions and isinstance(conditions, dict):
                if "attribute" in conditions:
                    update_kwargs["attribute"] = conditions["attribute"]
                if "equation" in conditions:
                    update_kwargs["condition"] = conditions["equation"]
                elif "condition" in conditions:
                    update_kwargs["condition"] = conditions["condition"]
                if "constant" in conditions:
                    update_kwargs["constant"] = str(conditions["constant"])

            # Update rule
            updated = self.rule_repository.update_rule(existing.id, **update_kwargs)

            if not updated:
                raise ConfigurationError(
                    f"Failed to update rule",
                    error_code="RULE_UPDATE_ERROR",
                    context={"rule_id": rule_id},
                )

            logger.info("Rule updated successfully", rule_id=rule_id)
            return self._rule_to_dict(updated)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update rule", rule_id=rule_id, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to update rule: {str(e)}",
                error_code="RULE_UPDATE_ERROR",
                context={"rule_id": rule_id, "error": str(e)},
            ) from e

    def delete_rule(self, rule_id: str) -> None:
        """
        Delete a rule.

        Args:
            rule_id: Rule identifier

        Raises:
            DataValidationError: If rule_id is empty or rule not found
            ConfigurationError: If rule cannot be deleted
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        logger.debug("Deleting rule", rule_id=rule_id)

        try:
            # Get existing rule
            existing = self.rule_repository.get_rule_by_rule_id(rule_id)
            if not existing:
                raise DataValidationError(
                    f"Rule with ID '{rule_id}' not found",
                    error_code="RULE_NOT_FOUND",
                    context={"rule_id": rule_id},
                )

            # Delete rule
            deleted = self.rule_repository.delete_rule(existing.id)

            if not deleted:
                raise ConfigurationError(
                    f"Failed to delete rule",
                    error_code="RULE_DELETE_ERROR",
                    context={"rule_id": rule_id},
                )

            logger.info("Rule deleted successfully", rule_id=rule_id)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete rule", rule_id=rule_id, error=str(e), exc_info=True
            )
            raise ConfigurationError(
                f"Failed to delete rule: {str(e)}",
                error_code="RULE_DELETE_ERROR",
                context={"rule_id": rule_id, "error": str(e)},
            ) from e

    def _rule_to_dict(self, rule: Rule) -> Dict[str, Any]:
        """
        Convert Rule model to dictionary format expected by API.

        Args:
            rule: Rule model instance

        Returns:
            Dictionary in rule engine format
        """
        return {
            "id": rule.rule_id,
            "rule_name": rule.rule_name,
            "conditions": {
                "attribute": rule.attribute,
                "equation": rule.condition,
                "constant": rule.constant,
            },
            "description": rule.message,
            "result": rule.action_result,
            "action_result": rule.action_result,
            "weight": rule.weight,
            "rule_point": rule.rule_point,
            "priority": rule.priority,
            "status": rule.status,
            "version": rule.version,
            "ruleset_id": rule.ruleset_id,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }


# Global service instance
_rule_management_service: Optional[RuleManagementService] = None


def get_rule_management_service() -> RuleManagementService:
    """
    Get the global rule management service instance.

    Returns:
        RuleManagementService instance
    """
    global _rule_management_service
    if _rule_management_service is None:
        _rule_management_service = RuleManagementService()
    return _rule_management_service
