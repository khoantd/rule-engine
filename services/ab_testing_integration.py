"""
A/B Testing Integration for Rule Execution.

This module provides integration utilities to support A/B testing
within the rule execution flow.
"""

from typing import Any, Dict, Optional

from common.logger import get_logger
from common.db_models import RuleABTest, RuleVersion
from common.db_connection import get_db_session

logger = get_logger(__name__)


def get_ab_test_variant(
    test_id: Optional[str],
    assignment_key: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Get the assigned variant for an A/B test.

    Args:
        test_id: A/B test identifier
        assignment_key: Assignment key (user ID, session ID, etc.)

    Returns:
        Dictionary with test information and variant, or None if no active test

    Raises:
        Exception: If variant assignment fails
    """
    if not test_id or not assignment_key:
        return None

    try:
        from services.ab_testing import get_ab_testing_service

        service = get_ab_testing_service()
        variant = service.assign_variant(
            test_id=test_id,
            assignment_key=assignment_key,
        )

        # Get test details
        test = service.get_test(test_id=test_id)
        if not test:
            logger.warning("A/B test not found", test_id=test_id)
            return None

        # Determine which version to use based on variant
        if variant == "A":
            version = test.get("variant_a_version")
        elif variant == "B":
            version = test.get("variant_b_version")
        else:
            logger.warning("Unknown variant", test_id=test_id, variant=variant)
            return None

        return {
            "test_id": test_id,
            "test": test,
            "variant": variant,
            "version": version,
        }

    except Exception as e:
        logger.error(
            "Failed to get A/B test variant",
            test_id=test_id,
            assignment_key=assignment_key,
            error=str(e),
            exc_info=True,
        )
        raise


def get_rule_by_version(
    rule_id: str,
    version: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a rule by its version string.

    Args:
        rule_id: Rule identifier
        version: Version string (e.g., "1.0", "2.1")

    Returns:
        Rule dictionary for the specified version, or None if not found

    Raises:
        Exception: If retrieval fails
    """
    if not rule_id or not version:
        return None

    session = get_db_session()
    try:
        # Get the rule version
        rule_version = (
            session.query(RuleVersion)
            .filter(
                RuleVersion.rule_id == rule_id,
                RuleVersion.version == version,
            )
            .first()
        )

        if not rule_version:
            logger.warning("Rule version not found", rule_id=rule_id, version=version)
            return None

        return rule_version.to_dict()

    except Exception as e:
        logger.error(
            "Failed to get rule by version",
            rule_id=rule_id,
            version=version,
            error=str(e),
            exc_info=True,
        )
        raise


def should_use_ab_test_variant(
    data: Dict[str, Any],
    test_id: Optional[str] = None,
) -> bool:
    """
    Determine if A/B testing should be applied to this execution.

    Args:
        data: Input data dictionary
        test_id: A/B test identifier

    Returns:
        True if A/B testing should be applied, False otherwise
    """
    if not test_id:
        return False

    session = get_db_session()
    try:
        # Check if test exists and is running
        test = session.query(RuleABTest).filter(RuleABTest.test_id == test_id).first()

        if not test:
            logger.warning("A/B test not found", test_id=test_id)
            return False

        if test.status != "running":
            logger.info(
                "A/B test not running",
                test_id=test_id,
                status=test.status,
            )
            return False

        return True

    except Exception as e:
        logger.error(
            "Failed to check A/B test status",
            test_id=test_id,
            error=str(e),
            exc_info=True,
        )
        return False


def get_assignment_key_from_data(data: Dict[str, Any]) -> Optional[str]:
    """
    Extract an assignment key from input data for A/B testing.

    Args:
        data: Input data dictionary

    Returns:
        Assignment key string or None

    Priorities:
        1. user_id field
        2. session_id field
        3. correlation_id field
        4. customer_id field
        5. Generate a hash of the entire data object
    """
    if not isinstance(data, dict) or not data:
        return None

    # Priority 1: user_id
    if "user_id" in data and data["user_id"]:
        return str(data["user_id"])

    # Priority 2: session_id
    if "session_id" in data and data["session_id"]:
        return str(data["session_id"])

    # Priority 3: correlation_id
    if "correlation_id" in data and data["correlation_id"]:
        return str(data["correlation_id"])

    # Priority 4: customer_id
    if "customer_id" in data and data["customer_id"]:
        return str(data["customer_id"])

    # Priority 5: Generate hash of data
    import hashlib
    import json

    try:
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:16]
        return data_hash
    except Exception as e:
        logger.warning("Failed to generate hash for assignment key", error=str(e))
        return None


def apply_ab_test_to_execution(
    data: Dict[str, Any],
    test_id: Optional[str] = None,
    assignment_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Apply A/B testing to rule execution.

    Args:
        data: Input data dictionary
        test_id: A/B test identifier
        assignment_key: Assignment key (auto-extracted if not provided)

    Returns:
        Dictionary with A/B test context information, or None if no active test

    Raises:
        Exception: If A/B test application fails
    """
    if not should_use_ab_test_variant(data, test_id):
        return None

    # Extract assignment key if not provided
    if not assignment_key:
        assignment_key = get_assignment_key_from_data(data)

    if not assignment_key:
        logger.warning("No assignment key available for A/B test", test_id=test_id)
        return None

    # Get variant assignment
    variant_info = get_ab_test_variant(test_id, assignment_key)

    if not variant_info:
        logger.warning("Failed to get variant assignment", test_id=test_id)
        return None

    logger.info(
        "A/B test applied",
        test_id=test_id,
        assignment_key=assignment_key,
        variant=variant_info["variant"],
        version=variant_info["version"],
    )

    return {
        "ab_test_id": test_id,
        "ab_test_variant": variant_info["variant"],
        "ab_test_version": variant_info["version"],
    }


def log_ab_test_execution(
    ab_test_id: Optional[str],
    ab_test_variant: Optional[str],
    execution_result: Dict[str, Any],
    execution_id: str,
) -> None:
    """
    Log A/B test execution to the database.

    Args:
        ab_test_id: A/B test identifier
        ab_test_variant: Assigned variant
        execution_result: Execution result dictionary
        execution_id: Execution identifier

    Raises:
        Exception: If logging fails
    """
    if not ab_test_id or not ab_test_variant:
        return

    session = get_db_session()
    try:
        from common.db_models import ExecutionLog

        # Find test by test_id
        test = (
            session.query(RuleABTest).filter(RuleABTest.test_id == ab_test_id).first()
        )

        if not test:
            logger.warning(
                "A/B test not found for execution logging", test_id=ab_test_id
            )
            return

        # Create or update execution log
        # Note: This is a simplified version. In production, you'd want to
        # update existing logs or create new ones based on your architecture
        logger.info(
            "A/B test execution logged",
            ab_test_id=ab_test_id,
            ab_test_variant=ab_test_variant,
            execution_id=execution_id,
        )

    except Exception as e:
        logger.error(
            "Failed to log A/B test execution",
            ab_test_id=ab_test_id,
            ab_test_variant=ab_test_variant,
            error=str(e),
            exc_info=True,
        )
