"""
Rule Versioning Service.

This module provides services for managing rule versions, including:
- Automatic version creation on rule updates
- Version rollback functionality
- Version comparison
- Version history tracking
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.db_models import Rule, RuleVersion, RuleStatus
from common.db_connection import get_db_session

logger = get_logger(__name__)


class RuleVersioningService:
    """
    Service for managing rule versions.

    This service provides functionality to:
    - Create new versions when rules are updated
    - Rollback to previous versions
    - Compare versions
    - Get version history
    """

    def __init__(self):
        """Initialize rule versioning service."""
        logger.debug("RuleVersioningService initialized")

    def create_version(
        self,
        rule: Rule,
        change_reason: Optional[str] = None,
        created_by: Optional[str] = None,
        db_session: Optional[Session] = None,
    ) -> RuleVersion:
        """
        Create a new version of a rule.

        Args:
            rule: The rule to create a version for
            change_reason: Reason for the change
            created_by: User who made the change
            db_session: Optional database session

        Returns:
            Created RuleVersion

        Raises:
            ConfigurationError: If version creation fails
        """
        if db_session is not None:
            return self._create_version_impl(
                rule, change_reason, created_by, db_session, commit_at_end=True
            )
        with get_db_session() as session:
            return self._create_version_impl(
                rule, change_reason, created_by, session, commit_at_end=False
            )

    def _create_version_impl(
        self,
        rule: Rule,
        change_reason: Optional[str],
        created_by: Optional[str],
        session: Session,
        commit_at_end: bool,
    ) -> RuleVersion:
        """Create a new version using the given session. Caller or context manager handles commit."""
        try:
            # Get latest version number for this rule
            latest_version = (
                session.query(RuleVersion)
                .filter(RuleVersion.rule_id == rule.rule_id)
                .order_by(RuleVersion.version_number.desc())
                .first()
            )

            version_number = 1
            if latest_version:
                version_number = latest_version.version_number + 1

            # Mark previous versions as not current
            session.query(RuleVersion).filter(
                RuleVersion.rule_id == rule.rule_id, RuleVersion.is_current == True
            ).update({"is_current": False})

            # Create new version
            version = RuleVersion(
                version_number=version_number,
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                attribute=rule.attribute,
                condition=rule.condition,
                constant=rule.constant,
                message=rule.message,
                weight=rule.weight,
                rule_point=rule.rule_point,
                priority=rule.priority,
                action_result=rule.action_result,
                status=rule.status,
                version=rule.version,
                ruleset_id=rule.ruleset_id,
                created_by=created_by,
                change_reason=change_reason,
                is_current=True,
                tags=rule.tags,
                extra_metadata=rule.extra_metadata,
            )

            session.add(version)
            if commit_at_end:
                session.commit()

            logger.info(
                "Rule version created",
                rule_id=rule.rule_id,
                version_number=version_number,
                change_reason=change_reason,
            )

            return version

        except Exception as e:
            session.rollback()
            logger.error(
                "Failed to create rule version",
                rule_id=rule.rule_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to create rule version: {str(e)}",
                error_code="VERSION_CREATE_ERROR",
                context={"rule_id": rule.rule_id, "error": str(e)},
            ) from e

    def get_version_history(
        self, rule_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a rule.

        Args:
            rule_id: Rule identifier
            limit: Maximum number of versions to return

        Returns:
            List of version dictionaries

        Raises:
            DataValidationError: If rule_id is empty
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        try:
            with get_db_session() as session:
                query = (
                    session.query(RuleVersion)
                    .filter(RuleVersion.rule_id == rule_id)
                    .order_by(RuleVersion.version_number.desc())
                )

                if limit:
                    query = query.limit(limit)

                versions = query.all()

                result = [v.to_dict() for v in versions]
                logger.info(
                    "Version history retrieved", rule_id=rule_id, count=len(result)
                )

                return result

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get version history",
                rule_id=rule_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to get version history: {str(e)}",
                error_code="VERSION_HISTORY_ERROR",
                context={"rule_id": rule_id, "error": str(e)},
            ) from e

    def get_version(
        self, rule_id: str, version_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific version of a rule.

        Args:
            rule_id: Rule identifier
            version_number: Version number

        Returns:
            Version dictionary if found, None otherwise

        Raises:
            DataValidationError: If rule_id is empty or version_number invalid
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        if version_number < 1:
            raise DataValidationError(
                "Version number must be positive", error_code="INVALID_VERSION"
            )

        try:
            with get_db_session() as session:
                version = (
                    session.query(RuleVersion)
                    .filter(
                        RuleVersion.rule_id == rule_id,
                        RuleVersion.version_number == version_number,
                    )
                    .first()
                )

                if not version:
                    logger.warning(
                        "Version not found",
                        rule_id=rule_id,
                        version_number=version_number,
                    )
                    return None

                logger.info(
                    "Version retrieved",
                    rule_id=rule_id,
                    version_number=version_number,
                )

                return version.to_dict()

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get version",
                rule_id=rule_id,
                version_number=version_number,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to get version: {str(e)}",
                error_code="VERSION_GET_ERROR",
                context={"rule_id": rule_id, "version_number": version_number},
            ) from e

    def rollback_to_version(
        self,
        rule_id: str,
        version_number: int,
        change_reason: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rollback a rule to a specific version.

        Args:
            rule_id: Rule identifier
            version_number: Version number to rollback to
            change_reason: Reason for the rollback
            created_by: User performing the rollback

        Returns:
            Updated rule dictionary

        Raises:
            DataValidationError: If rule_id or version invalid
            ConfigurationError: If rollback fails
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        if version_number < 1:
            raise DataValidationError(
                "Version number must be positive", error_code="INVALID_VERSION"
            )

        try:
            with get_db_session() as session:
                # Get target version
                target_version = (
                    session.query(RuleVersion)
                    .filter(
                        RuleVersion.rule_id == rule_id,
                        RuleVersion.version_number == version_number,
                    )
                    .first()
                )

                if not target_version:
                    raise DataValidationError(
                        f"Version {version_number} not found for rule {rule_id}",
                        error_code="VERSION_NOT_FOUND",
                        context={
                            "rule_id": rule_id,
                            "version_number": version_number,
                        },
                    )

                # Get current rule
                current_rule = (
                    session.query(Rule).filter(Rule.rule_id == rule_id).first()
                )

                if not current_rule:
                    raise DataValidationError(
                        f"Rule {rule_id} not found",
                        error_code="RULE_NOT_FOUND",
                        context={"rule_id": rule_id},
                    )

                # Create version of current state before rollback
                self.create_version(
                    current_rule,
                    change_reason=f"Pre-rollback backup: {change_reason or 'No reason provided'}",
                    created_by=created_by,
                    db_session=session,
                )

                # Update rule with target version data
                current_rule.rule_name = target_version.rule_name
                current_rule.attribute = target_version.attribute
                current_rule.condition = target_version.condition
                current_rule.constant = target_version.constant
                current_rule.message = target_version.message
                current_rule.weight = target_version.weight
                current_rule.rule_point = target_version.rule_point
                current_rule.priority = target_version.priority
                current_rule.action_result = target_version.action_result
                current_rule.updated_by = created_by

                # Mark target version as current
                session.query(RuleVersion).filter(
                    RuleVersion.rule_id == rule_id,
                    RuleVersion.is_current == True,
                ).update({"is_current": False})

                target_version.is_current = True

                session.commit()

                logger.info(
                    "Rule rolled back",
                    rule_id=rule_id,
                    to_version=version_number,
                    change_reason=change_reason,
                )

                return current_rule.to_dict()

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to rollback rule",
                rule_id=rule_id,
                version_number=version_number,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to rollback rule: {str(e)}",
                error_code="ROLLBACK_ERROR",
                context={
                    "rule_id": rule_id,
                    "version_number": version_number,
                    "error": str(e),
                },
            ) from e

    def compare_versions(
        self, rule_id: str, version_a: int, version_b: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of a rule.

        Args:
            rule_id: Rule identifier
            version_a: First version number
            version_b: Second version number

        Returns:
            Comparison dictionary with differences

        Raises:
            DataValidationError: If rule_id or versions invalid
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        if version_a < 1 or version_b < 1:
            raise DataValidationError(
                "Version numbers must be positive", error_code="INVALID_VERSION"
            )

        try:
            with get_db_session() as session:
                ver_a = (
                    session.query(RuleVersion)
                    .filter(
                        RuleVersion.rule_id == rule_id,
                        RuleVersion.version_number == version_a,
                    )
                    .first()
                )

                ver_b = (
                    session.query(RuleVersion)
                    .filter(
                        RuleVersion.rule_id == rule_id,
                        RuleVersion.version_number == version_b,
                    )
                    .first()
                )

                if not ver_a or not ver_b:
                    missing = []
                    if not ver_a:
                        missing.append(f"Version {version_a}")
                    if not ver_b:
                        missing.append(f"Version {version_b}")

                    raise DataValidationError(
                        f"Version(s) not found: {', '.join(missing)}",
                        error_code="VERSION_NOT_FOUND",
                        context={
                            "rule_id": rule_id,
                            "version_a": version_a,
                            "version_b": version_b,
                        },
                    )

                # Compare fields
                differences = {}

                fields_to_compare = [
                    "rule_name",
                    "attribute",
                    "condition",
                    "constant",
                    "message",
                    "weight",
                    "rule_point",
                    "priority",
                    "action_result",
                    "status",
                ]

                for field in fields_to_compare:
                    val_a = getattr(ver_a, field)
                    val_b = getattr(ver_b, field)

                    if val_a != val_b:
                        differences[field] = {
                            "version_a": val_a,
                            "version_b": val_b,
                            "changed": True,
                        }

                result = {
                    "rule_id": rule_id,
                    "version_a": version_a,
                    "version_b": version_b,
                    "version_a_data": ver_a.to_dict(),
                    "version_b_data": ver_b.to_dict(),
                    "differences": differences,
                    "has_differences": len(differences) > 0,
                }

                logger.info(
                    "Versions compared",
                    rule_id=rule_id,
                    version_a=version_a,
                    version_b=version_b,
                    differences_count=len(differences),
                )

                return result

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to compare versions",
                rule_id=rule_id,
                version_a=version_a,
                version_b=version_b,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to compare versions: {str(e)}",
                error_code="VERSION_COMPARE_ERROR",
                context={
                    "rule_id": rule_id,
                    "version_a": version_a,
                    "version_b": version_b,
                    "error": str(e),
                },
            ) from e

    def get_current_version(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current version of a rule.

        Args:
            rule_id: Rule identifier

        Returns:
            Current version dictionary if found, None otherwise

        Raises:
            DataValidationError: If rule_id is empty
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        try:
            with get_db_session() as session:
                version = (
                    session.query(RuleVersion)
                    .filter(
                        RuleVersion.rule_id == rule_id,
                        RuleVersion.is_current == True,
                    )
                    .first()
                )

                if not version:
                    logger.warning("No current version found", rule_id=rule_id)
                    return None

                logger.info("Current version retrieved", rule_id=rule_id)

                return version.to_dict()

        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get current version",
                rule_id=rule_id,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to get current version: {str(e)}",
                error_code="CURRENT_VERSION_ERROR",
                context={"rule_id": rule_id, "error": str(e)},
            ) from e


# Global service instance
_rule_versioning_service: Optional[RuleVersioningService] = None


def get_rule_versioning_service() -> RuleVersioningService:
    """
    Get the global rule versioning service instance.

    Returns:
        RuleVersioningService instance
    """
    global _rule_versioning_service
    if _rule_versioning_service is None:
        _rule_versioning_service = RuleVersioningService()
    return _rule_versioning_service
