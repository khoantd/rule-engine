"""
Rule Management Service with Database Integration.

This module provides services for managing Rules, including CRUD operations
using database storage.
"""

from typing import Any, Dict, List, Optional, Tuple

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.db_repository import RuleRepository, RulesetRepository, ConditionRepository
from common.db_models import Rule, RuleStatus, Condition
from common.db_connection import get_db_session
from sqlalchemy.orm import Session

logger = get_logger(__name__)


def _normalize_complex_mode(mode: Any) -> str:
    """
    Normalize API/file ``conditions.mode`` to engine values ``inclusive`` or ``exclusive``.

    Accepts inclusive/and and exclusive/or (case-insensitive).
    """
    if mode is None or (isinstance(mode, str) and not mode.strip()):
        raise DataValidationError(
            "Complex rules require conditions.mode (inclusive/and or exclusive/or).",
            error_code="RULE_COMPLEX_MODE_MISSING",
            context={"mode": mode},
        )
    m = str(mode).strip().lower()
    if m in ("inclusive", "and"):
        return "inclusive"
    if m in ("exclusive", "or"):
        return "exclusive"
    raise DataValidationError(
        f"Invalid conditions.mode {mode!r}; use inclusive/and or exclusive/or.",
        error_code="RULE_INVALID_COMPLEX_MODE",
        context={"mode": mode},
    )


def _resolve_rule_conditions_for_db(
    session: Session,
    conditions: Dict[str, Any],
    declared_type: Optional[str],
    base_metadata: Dict[str, Any],
) -> Tuple[str, str, str, Dict[str, Any]]:
    """
    Resolve API ``conditions`` into DB columns and optional ``metadata.rule_engine``.

    Supports:
    - Complex: ``items`` (non-empty list of condition IDs) and ``mode``.
    - Simple by reference: ``item``, ``condition_id``, or ``\"0\"`` (condition ID).
    - Inline: ``attribute`` + ``equation``/``condition`` + ``constant``.

    Returns:
        Tuple of (attribute, operator, constant, merged_metadata).
    """
    merged: Dict[str, Any] = dict(base_metadata)
    if isinstance(conditions, dict) and len(conditions) == 0:
        merged.pop("rule_engine", None)
        merged.pop("condition_ids", None)
        return "", "equal", "", merged

    raw_items = conditions.get("items") if isinstance(conditions, dict) else None

    if isinstance(raw_items, list) and len(raw_items) > 0:
        mode = _normalize_complex_mode(conditions.get("mode"))
        ids: List[str] = []
        for raw in raw_items:
            if raw is None or not str(raw).strip():
                raise DataValidationError(
                    "conditions.items must contain non-empty condition ID strings.",
                    error_code="RULE_COMPLEX_ITEM_EMPTY",
                    context={"items": raw_items},
                )
            ids.append(str(raw).strip())
        resolved = []
        for cid in ids:
            cond_model = session.query(Condition).filter(Condition.condition_id == cid).first()
            if not cond_model:
                raise DataValidationError(
                    f"Condition '{cid}' not found.",
                    error_code="CONDITION_NOT_FOUND",
                    context={"condition_id": cid},
                )
            resolved.append(cond_model)
        first = resolved[0]
        merged["rule_engine"] = {
            "type": "complex",
            "conditions": {"items": ids, "mode": mode},
        }
        merged.pop("condition_ids", None)
        return first.attribute, first.operator, str(first.value), merged

    if declared_type == "complex":
        raise DataValidationError(
            "type 'complex' requires conditions.items as a non-empty list of condition IDs.",
            error_code="RULE_COMPLEX_ITEMS_INVALID",
            context={"conditions": conditions},
        )

    condition_id: Optional[str] = None
    if "item" in conditions:
        condition_id = conditions.get("item")
    elif "condition_id" in conditions:
        condition_id = conditions.get("condition_id")
    elif "0" in conditions:
        condition_id = conditions.get("0")

    if condition_id is not None:
        cid = str(condition_id).strip()
        if not cid:
            raise DataValidationError(
                "Condition reference cannot be empty.",
                error_code="RULE_CONDITION_ID_EMPTY",
                context={"conditions": conditions},
            )
        cond_model = session.query(Condition).filter(Condition.condition_id == cid).first()
        if not cond_model:
            raise DataValidationError(
                f"Condition '{cid}' not found.",
                error_code="CONDITION_NOT_FOUND",
                context={"condition_id": cid},
            )
        merged["rule_engine"] = {"type": "simple", "conditions": {"item": cid}}
        merged["condition_ids"] = {"condition_id": cid}
        return cond_model.attribute, cond_model.operator, str(cond_model.value), merged

    if "attribute" in conditions:
        merged.pop("rule_engine", None)
        merged.pop("condition_ids", None)
        attribute = str(conditions.get("attribute", "") or "")
        condition_op = str(
            conditions.get("equation", conditions.get("condition", "equal")) or "equal"
        )
        cval = conditions.get("constant")
        constant = "" if cval is None else str(cval)
        return attribute, condition_op, constant, merged

    return "", "equal", "", merged


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
        condition_repository: Optional[ConditionRepository] = None,
    ):
        """
        Initialize rule management service.

        Args:
            rule_repository: Optional rule repository. If None, creates new instance.
            ruleset_repository: Optional ruleset repository. If None, creates new instance.
            condition_repository: Optional condition repository. If None, creates new instance.
        """
        self.rule_repository = rule_repository or RuleRepository()
        self.ruleset_repository = ruleset_repository or RulesetRepository()
        self.condition_repository = condition_repository or ConditionRepository()
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
            raise DataValidationError("Rule ID cannot be empty", error_code="RULE_ID_EMPTY")

        logger.debug("Getting rule", rule_id=rule_id)
        try:
            rule = self.rule_repository.get_rule_by_rule_id(rule_id)

            if not rule:
                logger.warning("Rule not found", rule_id=rule_id)
                return None

            logger.info("Rule found", rule_id=rule_id)
            return self._rule_to_dict(rule)
        except Exception as e:
            logger.error("Failed to get rule", rule_id=rule_id, error=str(e), exc_info=True)
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
                - conditions: One of: ``{"item": "C..."}`` / ``{"condition_id": ...}``,
                  ``{"items": [...], "mode": "inclusive"|"and"|"exclusive"|"or"}`` for complex,
                  or inline ``{"attribute", "equation", "constant"}``
                - description: Rule description
                - result: Result string
                - Optional: rule_point, weight, priority, type, action_result, metadata

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
            raise DataValidationError("Rule ID cannot be empty", error_code="RULE_ID_EMPTY")

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

            conditions = rule_data.get("conditions", {})
            if not isinstance(conditions, dict):
                raise DataValidationError(
                    "conditions must be a dictionary",
                    error_code="RULE_CONDITIONS_INVALID",
                    context={"conditions": conditions},
                )

            with get_db_session() as session:
                attribute, condition_op, constant, extra_metadata = _resolve_rule_conditions_for_db(
                    session,
                    conditions,
                    rule_data.get("type"),
                    dict(rule_data.get("metadata") or {}),
                )

            # Create rule in database
            rule = self.rule_repository.create_rule(
                rule_id=rule_id,
                rule_name=rule_data.get("rule_name", ""),
                attribute=attribute,
                condition=condition_op,
                constant=str(constant),
                ruleset_id=ruleset_id,
                message=rule_data.get("description", ""),
                weight=float(rule_data.get("weight", 1.0)),
                rule_point=int(rule_data.get("rule_point", 10)),
                priority=int(rule_data.get("priority", 0)),
                action_result=rule_data.get("result", rule_data.get("action_result", "Y")),
                status=RuleStatus.ACTIVE.value,
                version=rule_data.get("version", "1.0"),
                created_by=rule_data.get("created_by"),
                metadata=extra_metadata or None,
            )

            logger.info("Rule created successfully", rule_id=rule_id)
            return self._rule_to_dict(rule)

        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to create rule", rule_id=rule_id, error=str(e), exc_info=True)
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
            raise DataValidationError("Rule ID cannot be empty", error_code="RULE_ID_EMPTY")

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
            if "conditions" in rule_data:
                conditions = rule_data.get("conditions")
                if conditions is None:
                    pass
                elif not isinstance(conditions, dict):
                    raise DataValidationError(
                        "conditions must be a dictionary",
                        error_code="RULE_CONDITIONS_INVALID",
                        context={"conditions": conditions},
                    )
                else:
                    merged_meta = dict(existing.extra_metadata or {})
                    if isinstance(rule_data.get("metadata"), dict):
                        merged_meta.update(rule_data["metadata"])
                    with get_db_session() as session:
                        (
                            attribute,
                            condition_op,
                            constant,
                            merged_meta,
                        ) = _resolve_rule_conditions_for_db(
                            session,
                            conditions,
                            rule_data.get("type"),
                            merged_meta,
                        )
                    update_kwargs["attribute"] = attribute
                    update_kwargs["condition"] = condition_op
                    update_kwargs["constant"] = str(constant)
                    update_kwargs["extra_metadata"] = merged_meta

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
            logger.error("Failed to update rule", rule_id=rule_id, error=str(e), exc_info=True)
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
            raise DataValidationError("Rule ID cannot be empty", error_code="RULE_ID_EMPTY")

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
            logger.error("Failed to delete rule", rule_id=rule_id, error=str(e), exc_info=True)
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
        conditions: Dict[str, Any] = {
            "attribute": rule.attribute,
            "equation": rule.condition,
            "constant": rule.constant,
        }
        rule_type: Optional[str] = None

        if rule.extra_metadata:
            eng = rule.extra_metadata.get("rule_engine")
            if isinstance(eng, dict) and isinstance(eng.get("conditions"), dict):
                conditions = eng["conditions"]
                rule_type = eng.get("type")
            elif "condition_ids" in rule.extra_metadata:
                conditions = rule.extra_metadata["condition_ids"]

        out: Dict[str, Any] = {
            "id": rule.rule_id,
            "rule_name": rule.rule_name,
            "conditions": conditions,
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
            "metadata": rule.extra_metadata,
        }
        if rule_type is not None:
            out["type"] = rule_type
        return out


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
