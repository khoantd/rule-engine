"""
Database repository implementation for Rule Engine.

This module provides a ConfigRepository implementation backed by PostgreSQL/TimescaleDB.
It integrates with the existing repository pattern and supports CRUD operations for rules,
rulesets, conditions, actions, and actionset entries (stored as Pattern).
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from common.repository.config_repository import ConfigRepository
from common.db_models import (
    Ruleset,
    Rule,
    Condition,
    Attribute,
    Action,
    Pattern,
    RuleStatus,
    Base,
)
from common.db_connection import get_db_session
from common.logger import get_logger
from common.exceptions import ConfigurationError

logger = get_logger(__name__)


class DatabaseConfigRepository(ConfigRepository):
    """
    Database-backed configuration repository.

    This implementation uses PostgreSQL/TimescaleDB to store and retrieve
    rules, rulesets, conditions, actions, and actionset entries. It supports the same
    interface as FileConfigRepository and S3ConfigRepository for easy switching.
    """

    def __init__(self, default_ruleset_name: str = "default"):
        """
        Initialize database repository.

        Args:
            default_ruleset_name: Name of default ruleset to use when no specific ruleset is provided
        """
        self.default_ruleset_name = default_ruleset_name
        logger.info(
            "DatabaseConfigRepository initialized", default_ruleset=default_ruleset_name
        )

    def _get_ruleset_by_name(
        self, session: Session, ruleset_name: Optional[str] = None
    ) -> Optional[Ruleset]:
        """
        Get ruleset by name.

        Args:
            session: Database session
            ruleset_name: Ruleset name (uses default if None)

        Returns:
            Ruleset instance or None
        """
        ruleset_name = ruleset_name or self.default_ruleset_name

        return (
            session.query(Ruleset)
            .filter(
                and_(
                    Ruleset.name == ruleset_name,
                    Ruleset.status == RuleStatus.ACTIVE.value,
                )
            )
            .first()
        )

    def _get_default_or_active_ruleset(self, session: Session) -> Optional[Ruleset]:
        """
        Get default ruleset or first active ruleset.

        Args:
            session: Database session

        Returns:
            Ruleset instance or None
        """
        # Try to get default ruleset
        ruleset = (
            session.query(Ruleset)
            .filter(
                and_(
                    Ruleset.name == self.default_ruleset_name,
                    Ruleset.status == RuleStatus.ACTIVE.value,
                )
            )
            .first()
        )

        # If not found, try to get first active ruleset marked as default
        if not ruleset:
            ruleset = (
                session.query(Ruleset)
                .filter(
                    and_(
                        Ruleset.is_default == True,
                        Ruleset.status == RuleStatus.ACTIVE.value,
                    )
                )
                .first()
            )

        # If still not found, get first active ruleset
        if not ruleset:
            ruleset = (
                session.query(Ruleset)
                .filter(Ruleset.status == RuleStatus.ACTIVE.value)
                .order_by(Ruleset.created_at)
                .first()
            )

        return ruleset

    def read_rules_set(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read rules set from database.

        Args:
            source: Ruleset name (optional, uses default if None)

        Returns:
            List of rule dictionaries in the format expected by the rule engine

        Raises:
            ConfigurationError: If rules cannot be retrieved
        """
        logger.debug("Reading rules set from database", ruleset=source)

        try:
            with get_db_session() as session:
                # Get ruleset
                ruleset = self._get_ruleset_by_name(session, source)

                if not ruleset:
                    # Try to get any active ruleset
                    ruleset = self._get_default_or_active_ruleset(session)

                if not ruleset:
                    logger.warning("No active ruleset found", ruleset=source)
                    return []

                # Get rules ordered by priority
                rules = (
                    session.query(Rule)
                    .filter(
                        and_(
                            Rule.ruleset_id == ruleset.id,
                            Rule.status == RuleStatus.ACTIVE.value,
                        )
                    )
                    .order_by(Rule.priority.asc())
                    .all()
                )

                logger.info(
                    "Rules set loaded from database",
                    ruleset_name=ruleset.name,
                    rules_count=len(rules),
                )

                # Convert to expected format
                return [self._rule_to_dict(rule) for rule in rules]

        except Exception as e:
            logger.error(
                "Failed to read rules set from database",
                ruleset=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read rules set from database: {str(e)}",
                error_code="RULES_DB_READ_ERROR",
                context={"ruleset": source, "error": str(e)},
            ) from e

    def read_conditions_set(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read conditions set from database.

        Args:
            source: Currently unused (for future filtering)

        Returns:
            List of condition dictionaries

        Raises:
            ConfigurationError: If conditions cannot be retrieved
        """
        logger.debug("Reading conditions set from database")

        try:
            with get_db_session() as session:
                conditions = (
                    session.query(Condition)
                    .filter(Condition.status == RuleStatus.ACTIVE.value)
                    .all()
                )

                logger.info(
                    "Conditions set loaded from database",
                    conditions_count=len(conditions),
                )

                return [self._condition_to_dict(condition) for condition in conditions]

        except Exception as e:
            logger.error(
                "Failed to read conditions set from database",
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read conditions set from database: {str(e)}",
                error_code="CONDITIONS_DB_READ_ERROR",
                context={"error": str(e)},
            ) from e

    def read_patterns(self, source: Optional[str] = None) -> Dict[str, Any]:
        """
        Read actionset from database (stored as Pattern rows).

        Args:
            source: Ruleset name (optional, uses default if None)

        Returns:
            Dictionary mapping actionset keys (pattern_key) to action_recommendation

        Raises:
            ConfigurationError: If actionset cannot be retrieved
        """
        logger.debug("Reading actionset from database", ruleset=source)

        try:
            with get_db_session() as session:
                # Get ruleset
                ruleset = self._get_ruleset_by_name(session, source)

                if not ruleset:
                    ruleset = self._get_default_or_active_ruleset(session)

                if not ruleset:
                    logger.warning(
                        "No active ruleset found for actionset", ruleset=source
                    )
                    return {}

                # Get actionset entries (Pattern rows)
                patterns = (
                    session.query(Pattern)
                    .filter(Pattern.ruleset_id == ruleset.id)
                    .all()
                )

                logger.info(
                    "Actionset loaded from database",
                    ruleset_name=ruleset.name,
                    actionset_count=len(patterns),
                )

                # Convert to dictionary format (pattern_key -> action_recommendation)
                return {
                    pattern.pattern_key: pattern.action_recommendation
                    for pattern in patterns
                }

        except Exception as e:
            logger.error(
                "Failed to read actionset from database",
                ruleset=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read actionset from database: {str(e)}",
                error_code="PATTERNS_DB_READ_ERROR",
                context={"ruleset": source, "error": str(e)},
            ) from e

    def read_json(
        self, source: Optional[str] = None
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Read configuration as JSON from database.

        Args:
            source: Ruleset name (optional)

        Returns:
            Dictionary containing rules_set and patterns (actionset key -> action_recommendation)

        Raises:
            ConfigurationError: If configuration cannot be retrieved
        """
        logger.debug("Reading JSON configuration from database", ruleset=source)

        try:
            rules_set = self.read_rules_set(source)
            patterns = self.read_patterns(source)

            result = {"rules_set": rules_set, "patterns": patterns}

            logger.info("JSON configuration loaded from database", source=source)
            return result

        except Exception as e:
            logger.error(
                "Failed to read JSON configuration from database",
                ruleset=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read JSON configuration from database: {str(e)}",
                error_code="JSON_DB_READ_ERROR",
                context={"ruleset": source, "error": str(e)},
            ) from e

    def _rule_to_dict(self, rule: Rule) -> Dict[str, Any]:
        """
        Convert Rule model to dictionary format expected by rule engine.

        Args:
            rule: Rule model instance

        Returns:
            Dictionary in rule engine format
        """
        return {
            "id": rule.rule_id,
            "rule_name": rule.rule_name,
            "attribute": rule.attribute,
            "condition": rule.condition,
            "constant": rule.constant,
            "message": rule.message,
            "weight": rule.weight,
            "rule_point": rule.rule_point,
            "priority": rule.priority,
            "action_result": rule.action_result,
        }

    def _condition_to_dict(self, condition: Condition) -> Dict[str, Any]:
        """
        Convert Condition model to dictionary format.

        Args:
            condition: Condition model instance

        Returns:
            Dictionary in rule engine format
        """
        return {
            "id": condition.condition_id,
            "name": condition.name,
            "attribute": condition.attribute,
            "operator": condition.operator,
            "value": condition.value,
        }


class RulesetRepository:
    """
    Repository for Ruleset CRUD operations.
    """

    def create_ruleset(
        self,
        name: str,
        description: Optional[str] = None,
        version: str = "1.0",
        tenant_id: Optional[str] = None,
        is_default: bool = False,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> Ruleset:
        """
        Create a new ruleset.

        Args:
            name: Ruleset name
            description: Ruleset description
            version: Ruleset version
            tenant_id: Tenant ID for multi-tenancy
            is_default: Whether this is the default ruleset
            tags: List of tags
            metadata: Additional metadata
            created_by: User who created the ruleset

        Returns:
            Created Ruleset instance
        """
        with get_db_session() as session:
            ruleset = Ruleset(
                name=name,
                description=description,
                version=version,
                tenant_id=tenant_id,
                is_default=is_default,
                tags=tags,
                extra_metadata=metadata,
                created_by=created_by,
                updated_by=created_by,
            )

            session.add(ruleset)
            session.flush()  # Flush to get the ID

            logger.info("Ruleset created", ruleset_id=ruleset.id, name=name)

            return ruleset

    def get_ruleset(self, ruleset_id: int) -> Optional[Ruleset]:
        """
        Get ruleset by ID.

        Args:
            ruleset_id: Ruleset ID

        Returns:
            Ruleset instance or None
        """
        with get_db_session() as session:
            return session.query(Ruleset).filter(Ruleset.id == ruleset_id).first()

    def get_ruleset_by_name(self, name: str) -> Optional[Ruleset]:
        """
        Get ruleset by name.

        Args:
            name: Ruleset name

        Returns:
            Ruleset instance or None
        """
        with get_db_session() as session:
            return session.query(Ruleset).filter(Ruleset.name == name).first()

    def get_default_ruleset(self) -> Optional[Ruleset]:
        """
        Get the default ruleset (is_default=True and active) or first active ruleset.

        Returns:
            Ruleset instance or None
        """
        with get_db_session() as session:
            ruleset = (
                session.query(Ruleset)
                .filter(
                    and_(
                        Ruleset.is_default == True,
                        Ruleset.status == RuleStatus.ACTIVE.value,
                    )
                )
                .order_by(Ruleset.created_at.asc())
                .first()
            )
            if ruleset:
                return ruleset
            return (
                session.query(Ruleset)
                .filter(Ruleset.status == RuleStatus.ACTIVE.value)
                .order_by(Ruleset.created_at.asc())
                .first()
            )

    def list_rulesets(
        self,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Ruleset]:
        """
        List rulesets with optional filters.

        Args:
            status: Filter by status
            tenant_id: Filter by tenant ID
            limit: Maximum number of results

        Returns:
            List of Ruleset instances
        """
        with get_db_session() as session:
            query = session.query(Ruleset)

            if status:
                query = query.filter(Ruleset.status == status)

            if tenant_id:
                query = query.filter(Ruleset.tenant_id == tenant_id)

            return query.order_by(Ruleset.created_at.desc()).limit(limit).all()

    def update_ruleset(self, ruleset_id: int, **kwargs) -> Optional[Ruleset]:
        """
        Update ruleset.

        Args:
            ruleset_id: Ruleset ID
            **kwargs: Fields to update

        Returns:
            Updated Ruleset instance or None
        """
        with get_db_session() as session:
            ruleset = session.query(Ruleset).filter(Ruleset.id == ruleset_id).first()

            if not ruleset:
                return None

            for key, value in kwargs.items():
                if hasattr(ruleset, key):
                    setattr(ruleset, key, value)

            logger.info("Ruleset updated", ruleset_id=ruleset_id)
            return ruleset

    def delete_ruleset(self, ruleset_id: int) -> bool:
        """
        Delete ruleset (cascades to rules and actionset entries / patterns).

        Args:
            ruleset_id: Ruleset ID

        Returns:
            True if deleted, False if not found
        """
        with get_db_session() as session:
            ruleset = session.query(Ruleset).filter(Ruleset.id == ruleset_id).first()

            if not ruleset:
                return False

            session.delete(ruleset)

            logger.info("Ruleset deleted", ruleset_id=ruleset_id)
            return True


class RuleRepository:
    """
    Repository for Rule CRUD operations.
    """

    def create_rule(
        self,
        rule_id: str,
        rule_name: str,
        attribute: str,
        condition: str,
        constant: str,
        ruleset_id: int,
        message: Optional[str] = None,
        weight: float = 1.0,
        rule_point: int = 0,
        priority: int = 0,
        action_result: str = "Y",
        status: str = RuleStatus.ACTIVE.value,
        version: str = "1.0",
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> Rule:
        """
        Create a new rule.

        Args:
            rule_id: Unique rule identifier
            rule_name: Human-readable rule name
            attribute: Data attribute to evaluate
            condition: Condition operator
            constant: Constant value for comparison
            ruleset_id: Ruleset ID
            message: Rule message
            weight: Weight multiplier
            rule_point: Base points
            priority: Execution priority
            action_result: Action result character
            status: Rule status
            version: Rule version
            tags: List of tags
            metadata: Additional metadata
            created_by: User who created the rule

        Returns:
            Created Rule instance
        """
        with get_db_session() as session:
            rule = Rule(
                rule_id=rule_id,
                rule_name=rule_name,
                attribute=attribute,
                condition=condition,
                constant=constant,
                message=message,
                weight=weight,
                rule_point=rule_point,
                priority=priority,
                action_result=action_result,
                status=status,
                version=version,
                ruleset_id=ruleset_id,
                tags=tags,
                extra_metadata=metadata,
                created_by=created_by,
                updated_by=created_by,
            )

            session.add(rule)
            session.flush()

            logger.info("Rule created", rule_id=rule.id, name=rule_name)

            return rule

    def get_rule(self, rule_id: int) -> Optional[Rule]:
        """
        Get rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            Rule instance or None
        """
        with get_db_session() as session:
            return session.query(Rule).filter(Rule.id == rule_id).first()

    def get_rule_by_rule_id(self, rule_identifier: str) -> Optional[Rule]:
        """
        Get rule by rule_id field.

        Args:
            rule_identifier: Rule identifier string

        Returns:
            Rule instance or None
        """
        with get_db_session() as session:
            return session.query(Rule).filter(Rule.rule_id == rule_identifier).first()

    def list_rules(
        self,
        ruleset_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Rule]:
        """
        List rules with optional filters.

        Args:
            ruleset_id: Filter by ruleset ID
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of Rule instances
        """
        with get_db_session() as session:
            query = session.query(Rule)

            if ruleset_id:
                query = query.filter(Rule.ruleset_id == ruleset_id)

            if status:
                query = query.filter(Rule.status == status)

            return query.order_by(Rule.priority.asc()).limit(limit).all()

    def update_rule(self, rule_id: int, **kwargs) -> Optional[Rule]:
        """
        Update rule.

        Args:
            rule_id: Rule ID
            **kwargs: Fields to update

        Returns:
            Updated Rule instance or None
        """
        with get_db_session() as session:
            rule = session.query(Rule).filter(Rule.id == rule_id).first()

            if not rule:
                return None

            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)

            logger.info("Rule updated", rule_id=rule_id)
            return rule

    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete rule.

        Args:
            rule_id: Rule ID

        Returns:
            True if deleted, False if not found
        """
        with get_db_session() as session:
            rule = session.query(Rule).filter(Rule.id == rule_id).first()

            if not rule:
                return False

            session.delete(rule)

            logger.info("Rule deleted", rule_id=rule_id)
            return True


class ConditionRepository:
    """
    Repository for Condition CRUD operations.
    """

    def create_condition(
        self,
        condition_id: str,
        name: str,
        attribute: str,
        operator: str,
        value: str,
        description: Optional[str] = None,
        status: str = RuleStatus.ACTIVE.value,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> Condition:
        """Create a new condition."""
        with get_db_session() as session:
            condition = Condition(
                condition_id=condition_id,
                name=name,
                description=description,
                attribute=attribute,
                operator=operator,
                value=value,
                status=status,
                tags=tags,
                extra_metadata=metadata,
                created_by=created_by,
                updated_by=created_by,
            )

            session.add(condition)
            session.flush()

            logger.info("Condition created", condition_id=condition.id, name=name)
            return condition

    def get_condition(self, condition_id: int) -> Optional[Condition]:
        """Get condition by ID."""
        with get_db_session() as session:
            return session.query(Condition).filter(Condition.id == condition_id).first()

    def list_conditions(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Condition]:
        """List conditions with optional filters."""
        with get_db_session() as session:
            query = session.query(Condition)

            if status:
                query = query.filter(Condition.status == status)

            return query.order_by(Condition.created_at.desc()).limit(limit).all()

    def delete_condition(self, condition_id: int) -> bool:
        """Delete condition."""
        with get_db_session() as session:
            condition = (
                session.query(Condition).filter(Condition.id == condition_id).first()
            )

            if not condition:
                return False

            session.delete(condition)
            logger.info("Condition deleted", condition_id=condition_id)
            return True

    def get_condition_by_condition_id(self, condition_id: str) -> Optional[Condition]:
        """Get condition by condition_id string."""
        with get_db_session() as session:
            return (
                session.query(Condition)
                .filter(Condition.condition_id == condition_id)
                .first()
            )


class AttributeRepository:
    """
    Repository for Attribute (fact) CRUD operations.
    """

    def create_attribute(
        self,
        attribute_id: str,
        name: str,
        data_type: str = "string",
        description: Optional[str] = None,
        status: str = RuleStatus.ACTIVE.value,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> Attribute:
        """Create a new attribute (fact)."""
        with get_db_session() as session:
            attribute = Attribute(
                attribute_id=attribute_id,
                name=name,
                description=description,
                data_type=data_type,
                status=status,
                tags=tags,
                extra_metadata=metadata,
                created_by=created_by,
                updated_by=created_by,
            )

            session.add(attribute)
            session.flush()

            logger.info(
                "Attribute created", attribute_id=attribute.id, name=name
            )
            return attribute

    def get_attribute(self, pk: int) -> Optional[Attribute]:
        """Get attribute by primary key."""
        with get_db_session() as session:
            return session.query(Attribute).filter(Attribute.id == pk).first()

    def get_attribute_by_attribute_id(self, attribute_id: str) -> Optional[Attribute]:
        """Get attribute by attribute_id string."""
        with get_db_session() as session:
            return (
                session.query(Attribute)
                .filter(Attribute.attribute_id == attribute_id)
                .first()
            )

    def list_attributes(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Attribute]:
        """List attributes with optional filters."""
        with get_db_session() as session:
            query = session.query(Attribute)

            if status:
                query = query.filter(Attribute.status == status)

            return query.order_by(Attribute.attribute_id.asc()).limit(limit).all()

    def delete_attribute(self, pk: int) -> bool:
        """Delete attribute by primary key."""
        with get_db_session() as session:
            attribute = session.query(Attribute).filter(Attribute.id == pk).first()

            if not attribute:
                return False

            session.delete(attribute)
            logger.info("Attribute deleted", attribute_id=pk)
            return True


class ActionRepository:
    """
    Repository for Action CRUD operations.
    """

    def create_action(
        self,
        action_id: str,
        name: str,
        action_type: str,
        configuration: dict,
        description: Optional[str] = None,
        status: str = RuleStatus.ACTIVE.value,
        pattern_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> Action:
        """Create a new action."""
        with get_db_session() as session:
            action = Action(
                action_id=action_id,
                name=name,
                description=description,
                action_type=action_type,
                configuration=configuration,
                status=status,
                pattern_id=pattern_id,
                tags=tags,
                extra_metadata=metadata,
                created_by=created_by,
                updated_by=created_by,
            )

            session.add(action)
            session.flush()

            logger.info("Action created", action_id=action.id, name=name)
            return action

    def get_action(self, action_id: int) -> Optional[Action]:
        """Get action by ID."""
        with get_db_session() as session:
            return session.query(Action).filter(Action.id == action_id).first()

    def list_actions(
        self,
        status: Optional[str] = None,
        pattern_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Action]:
        """List actions with optional filters."""
        with get_db_session() as session:
            query = session.query(Action)

            if status:
                query = query.filter(Action.status == status)
            if pattern_id is not None:
                query = query.filter(Action.pattern_id == pattern_id)

            return query.order_by(Action.created_at.desc()).limit(limit).all()

    def delete_action(self, action_id: int) -> bool:
        """Delete action."""
        with get_db_session() as session:
            action = session.query(Action).filter(Action.id == action_id).first()

            if not action:
                return False

            session.delete(action)
            logger.info("Action deleted", action_id=action_id)
            return True
