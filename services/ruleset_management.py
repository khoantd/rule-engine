"""
RuleSet Management Service with Database Integration.

This module provides services for managing RuleSets, including CRUD operations
using database storage.
"""

from typing import Any, Dict, List, Optional

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.db_repository import RulesetRepository, RuleRepository
from common.db_models import Ruleset, Pattern, Rule, RuleStatus
from common.db_connection import get_db_session

logger = get_logger(__name__)

# Logical name used by API/UI for the default ruleset (resolved to is_default=True)
DEFAULT_RULESET_LOGICAL_NAME = "default_ruleset"


class RuleSetManagementService:
    """
    Service for managing RuleSets using database storage.

    This service provides CRUD operations for RuleSets, using database
    for persistence.
    """

    def __init__(
        self,
        ruleset_repository: Optional[RulesetRepository] = None,
        rule_repository: Optional[RuleRepository] = None,
    ):
        """
        Initialize ruleset management service.

        Args:
            ruleset_repository: Optional ruleset repository. If None, creates new instance.
            rule_repository: Optional rule repository. If None, creates new instance.
        """
        self.ruleset_repository = ruleset_repository or RulesetRepository()
        self.rule_repository = rule_repository or RuleRepository()
        logger.debug("RuleSetManagementService initialized")

    def list_rulesets(self) -> List[Dict[str, Any]]:
        """
        List all rulesets.

        Returns:
            List of ruleset dictionaries
        """
        logger.debug("Listing all rulesets")
        try:
            with get_db_session() as session:
                # Query all active rulesets
                rulesets = (
                    session.query(Ruleset)
                    .filter(Ruleset.status == RuleStatus.ACTIVE.value)
                    .order_by(Ruleset.created_at.desc())
                    .all()
                )

                # Convert to dict with rules and actionset
                result = []
                for ruleset in rulesets:
                    result.append(self._ruleset_to_dict(ruleset))

                logger.info("Rulesets listed successfully", count=len(result))
                return result
        except Exception as e:
            logger.error("Failed to list rulesets", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list rulesets: {str(e)}",
                error_code="RULESETS_LIST_ERROR",
                context={"error": str(e)},
            ) from e

    def get_ruleset(self, ruleset_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a ruleset by name.

        Args:
            ruleset_name: RuleSet name

        Returns:
            RuleSet dictionary if found, None otherwise

        Raises:
            DataValidationError: If ruleset_name is empty
        """
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty", error_code="RULESET_NAME_EMPTY"
            )

        logger.debug("Getting ruleset", ruleset_name=ruleset_name)
        try:
            with get_db_session() as session:
                # Resolve "default_ruleset" to the ruleset marked is_default=True (or first active)
                if ruleset_name == DEFAULT_RULESET_LOGICAL_NAME:
                    ruleset = (
                        session.query(Ruleset)
                        .filter(
                            Ruleset.is_default == True,
                            Ruleset.status == RuleStatus.ACTIVE.value,
                        )
                        .order_by(Ruleset.created_at.asc())
                        .first()
                    )
                    if not ruleset:
                        ruleset = (
                            session.query(Ruleset)
                            .filter(Ruleset.status == RuleStatus.ACTIVE.value)
                            .order_by(Ruleset.created_at.asc())
                            .first()
                        )
                else:
                    ruleset = (
                        session.query(Ruleset)
                        .filter(
                            Ruleset.name == ruleset_name,
                            Ruleset.status == RuleStatus.ACTIVE.value,
                        )
                        .first()
                    )

                if not ruleset:
                    logger.warning("RuleSet not found", ruleset_name=ruleset_name)
                    return None

                logger.info("RuleSet found", ruleset_name=ruleset_name)
                return self._ruleset_to_dict(ruleset)
        except Exception as e:
            logger.error(
                "Failed to get ruleset",
                ruleset_name=ruleset_name,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to get ruleset {ruleset_name}: {str(e)}",
                error_code="RULESET_GET_ERROR",
                context={"ruleset_name": ruleset_name, "error": str(e)},
            ) from e

    def create_ruleset(self, ruleset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new ruleset.

        Args:
            ruleset_data: RuleSet data dictionary. Must include:
                - ruleset_name: RuleSet name
                Optional fields:
                - description: RuleSet description
                - version: RuleSet version
                - rules: List of rule dictionaries (will be created)
                - actionset: List of actionset entries (pattern key strings or dicts with "pattern"/"message")

        Returns:
            Created RuleSet dictionary

        Raises:
            DataValidationError: If ruleset data is invalid or ruleset name already exists
            ConfigurationError: If ruleset cannot be created
        """
        logger.debug("Creating ruleset", ruleset_name=ruleset_data.get("ruleset_name"))

        # Validate required fields
        if "ruleset_name" not in ruleset_data:
            raise DataValidationError(
                "Missing required field: ruleset_name",
                error_code="RULESET_FIELD_MISSING",
                context={"field": "ruleset_name"},
            )

        ruleset_name = ruleset_data["ruleset_name"]
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty", error_code="RULESET_NAME_EMPTY"
            )

        try:
            # Check if ruleset already exists
            existing_ruleset = self.get_ruleset(ruleset_name)
            if existing_ruleset:
                raise DataValidationError(
                    f"RuleSet with name '{ruleset_name}' already exists",
                    error_code="RULESET_NAME_EXISTS",
                    context={"ruleset_name": ruleset_name},
                )

            with get_db_session() as session:
                # Create ruleset
                ruleset = self.ruleset_repository.create_ruleset(
                    name=ruleset_name,
                    description=ruleset_data.get("description"),
                    version=ruleset_data.get("version", "1.0"),
                    tenant_id=ruleset_data.get("tenant_id"),
                    is_default=ruleset_data.get("is_default", False),
                    tags=ruleset_data.get("tags"),
                    metadata=ruleset_data.get("metadata"),
                    created_by=ruleset_data.get("created_by"),
                    session=session,
                )

                # Create actionset entries if provided
                actionset = ruleset_data.get("actionset", [])
                if actionset and isinstance(actionset, list):
                    for actionset_item in actionset:
                        if isinstance(actionset_item, dict):
                            pattern_key = actionset_item.get("pattern")
                            message = actionset_item.get("message")
                        else:
                            pattern_key = str(actionset_item)
                            message = ""

                        if pattern_key:
                            pattern_obj = Pattern(
                                pattern_key=pattern_key,
                                action_recommendation=message
                                or f"Action for {pattern_key}",
                                description=f"Actionset entry {pattern_key}",
                                ruleset_id=ruleset.id,
                            )
                            session.add(pattern_obj)

                # Create rules if provided
                rules = ruleset_data.get("rules", [])
                if rules and isinstance(rules, list):
                    for rule_data in rules:
                        if isinstance(rule_data, dict):
                            self._create_rule_from_dict(session, rule_data, ruleset.id)

                session.flush()

                logger.info("RuleSet created successfully", ruleset_name=ruleset_name)
                return self._ruleset_to_dict(ruleset)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to create ruleset",
                ruleset_name=ruleset_name,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to create ruleset: {str(e)}",
                error_code="RULESET_CREATE_ERROR",
                context={"ruleset_name": ruleset_name, "error": str(e)},
            ) from e

    def update_ruleset(
        self, ruleset_name: str, ruleset_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing ruleset.

        Args:
            ruleset_name: RuleSet name
            ruleset_data: Updated RuleSet data dictionary

        Returns:
            Updated RuleSet dictionary

        Raises:
            DataValidationError: If ruleset_name is empty or ruleset not found
            ConfigurationError: If ruleset cannot be updated
        """
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty", error_code="RULESET_NAME_EMPTY"
            )

        logger.debug("Updating ruleset", ruleset_name=ruleset_name)

        try:
            with get_db_session() as session:
                # Get existing ruleset
                ruleset = (
                    session.query(Ruleset)
                    .filter(
                        Ruleset.name == ruleset_name,
                        Ruleset.status == RuleStatus.ACTIVE.value,
                    )
                    .first()
                )

                if not ruleset:
                    raise DataValidationError(
                        f"RuleSet with name '{ruleset_name}' not found",
                        error_code="RULESET_NOT_FOUND",
                        context={"ruleset_name": ruleset_name},
                    )

                # Update ruleset fields
                if "description" in ruleset_data:
                    ruleset.description = ruleset_data["description"]
                if "version" in ruleset_data:
                    ruleset.version = ruleset_data["version"]
                if "status" in ruleset_data:
                    ruleset.status = ruleset_data["status"]
                if "tags" in ruleset_data:
                    ruleset.tags = ruleset_data["tags"]
                if "metadata" in ruleset_data:
                    ruleset.extra_metadata = ruleset_data["metadata"]

                session.flush()

                logger.info("RuleSet updated successfully", ruleset_name=ruleset_name)
                return self._ruleset_to_dict(ruleset)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update ruleset",
                ruleset_name=ruleset_name,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to update ruleset: {str(e)}",
                error_code="RULESET_UPDATE_ERROR",
                context={"ruleset_name": ruleset_name, "error": str(e)},
            ) from e

    def delete_ruleset(self, ruleset_name: str) -> None:
        """
        Delete a ruleset.

        Args:
            ruleset_name: RuleSet name

        Raises:
            DataValidationError: If ruleset_name is empty or ruleset not found
            ConfigurationError: If ruleset cannot be deleted
        """
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty", error_code="RULESET_NAME_EMPTY"
            )

        logger.debug("Deleting ruleset", ruleset_name=ruleset_name)

        try:
            # Get existing ruleset
            with get_db_session() as session:
                ruleset = (
                    session.query(Ruleset)
                    .filter(
                        Ruleset.name == ruleset_name,
                        Ruleset.status == RuleStatus.ACTIVE.value,
                    )
                    .first()
                )

                if not ruleset:
                    raise DataValidationError(
                        f"RuleSet with name '{ruleset_name}' not found",
                        error_code="RULESET_NOT_FOUND",
                        context={"ruleset_name": ruleset_name},
                    )

                # Delete ruleset (cascades to rules and actionset entries)
                session.delete(ruleset)

                logger.info("RuleSet deleted successfully", ruleset_name=ruleset_name)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete ruleset",
                ruleset_name=ruleset_name,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to delete ruleset: {str(e)}",
                error_code="RULESET_DELETE_ERROR",
                context={"ruleset_name": ruleset_name, "error": str(e)},
            ) from e

    def _create_rule_from_dict(
        self, session, rule_data: Dict[str, Any], ruleset_id: int
    ) -> Rule:
        """
        Create a rule from dictionary data.

        Args:
            session: Database session
            rule_data: Rule data dictionary
            ruleset_id: Ruleset ID

        Returns:
            Created Rule instance
        """
        conditions = rule_data.get("conditions", {})

        # Handle conditions - could be inline or reference
        if isinstance(conditions, dict):
            attribute = conditions.get("attribute", "")
            condition = conditions.get("equation", conditions.get("condition", "equal"))
            constant = conditions.get("constant", "")
        else:
            attribute = ""
            condition = "equal"
            constant = ""

        rule = Rule(
            rule_id=rule_data.get("id", ""),
            rule_name=rule_data.get("rule_name", ""),
            attribute=attribute,
            condition=condition,
            constant=str(constant),
            message=rule_data.get("description", ""),
            weight=float(rule_data.get("weight", 1.0)),
            rule_point=int(rule_data.get("rule_point", 10)),
            priority=int(rule_data.get("priority", 0)),
            action_result=rule_data.get("result", rule_data.get("action_result", "Y")),
            status=RuleStatus.ACTIVE.value,
            version=rule_data.get("version", "1.0"),
            ruleset_id=ruleset_id,
            created_by=rule_data.get("created_by"),
        )

        session.add(rule)
        return rule

    def _ruleset_to_dict(self, ruleset: Ruleset) -> Dict[str, Any]:
        """
        Convert Ruleset model to dictionary format expected by API.

        Args:
            ruleset: Ruleset model instance

        Returns:
            Dictionary in rule engine format including rules and actionset
        """
        # rules is lazy="dynamic"; ruleset.patterns holds actionset entries (Pattern model)
        rules_list = list(ruleset.rules.all()) if hasattr(ruleset.rules, "all") else list(ruleset.rules)
        rules_data = [r.to_dict() for r in rules_list]
        actionset_data = [p.pattern_key for p in (ruleset.patterns or [])]

        return {
            "ruleset_name": ruleset.name,
            "description": ruleset.description,
            "version": ruleset.version,
            "status": ruleset.status,
            "tenant_id": ruleset.tenant_id,
            "is_default": ruleset.is_default,
            "tags": ruleset.tags,
            "metadata": ruleset.extra_metadata,
            "created_at": ruleset.created_at.isoformat()
            if ruleset.created_at
            else None,
            "updated_at": ruleset.updated_at.isoformat()
            if ruleset.updated_at
            else None,
            "rules": rules_data,
            "actionset": actionset_data,
        }


# Global service instance
_ruleset_management_service: Optional[RuleSetManagementService] = None


def get_ruleset_management_service() -> RuleSetManagementService:
    """
    Get global ruleset management service instance.

    Returns:
        RuleSetManagementService instance
    """
    global _ruleset_management_service
    if _ruleset_management_service is None:
        _ruleset_management_service = RuleSetManagementService()
    return _ruleset_management_service
