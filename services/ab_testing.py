"""
A/B Testing Service.

This module provides services for managing A/B testing of rules, including:
- Test creation and configuration
- Variant assignment using hash-based routing
- Test metrics collection and analysis
- Statistical significance testing
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.db_models import (
    RuleABTest,
    TestAssignment,
    ExecutionLog,
    RuleStatus,
)
from common.db_connection import get_db_session

logger = get_logger(__name__)


class ABTestingService:
    """
    Service for managing A/B tests on rules.

    This service provides functionality to:
    - Create and manage A/B tests
    - Assign users/requests to variants
    - Track test metrics
    - Analyze results with statistical significance
    """

    def __init__(self):
        """Initialize A/B testing service."""
        logger.debug("ABTestingService initialized")

    def create_test(
        self,
        test_id: str,
        test_name: str,
        rule_id: str,
        ruleset_id: int,
        variant_a_version: str,
        variant_b_version: str,
        description: Optional[str] = None,
        traffic_split_a: float = 0.5,
        traffic_split_b: float = 0.5,
        variant_a_description: Optional[str] = None,
        variant_b_description: Optional[str] = None,
        duration_hours: Optional[int] = None,
        min_sample_size: Optional[int] = None,
        confidence_level: float = 0.95,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new A/B test.

        Args:
            test_id: Unique test identifier
            test_name: Test name
            rule_id: Target rule ID
            ruleset_id: Ruleset ID
            variant_a_version: Version string for variant A (control)
            variant_b_version: Version string for variant B (treatment)
            description: Test description
            traffic_split_a: Traffic split for variant A (0-1)
            traffic_split_b: Traffic split for variant B (0-1)
            variant_a_description: Description of variant A
            variant_b_description: Description of variant B
            duration_hours: Test duration in hours
            min_sample_size: Minimum sample size per variant
            confidence_level: Statistical confidence level (0-1)
            created_by: User creating the test
            tags: Optional tags
            metadata: Optional metadata

        Returns:
            Created test dictionary

        Raises:
            DataValidationError: If validation fails
            ConfigurationError: If creation fails
        """
        # Validate inputs
        if not test_id or not test_id.strip():
            raise DataValidationError(
                "Test ID cannot be empty", error_code="TEST_ID_EMPTY"
            )

        if not test_name or not test_name.strip():
            raise DataValidationError(
                "Test name cannot be empty", error_code="TEST_NAME_EMPTY"
            )

        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        if not (0 <= traffic_split_a <= 1) or not (0 <= traffic_split_b <= 1):
            raise DataValidationError(
                "Traffic splits must be between 0 and 1",
                error_code="INVALID_TRAFFIC_SPLIT",
            )

        if abs(traffic_split_a + traffic_split_b - 1.0) > 0.01:
            raise DataValidationError(
                "Traffic splits must sum to 1.0",
                error_code="TRAFFIC_SPLIT_SUM_ERROR",
            )

        if not (0 < confidence_level <= 1):
            raise DataValidationError(
                "Confidence level must be between 0 and 1 (exclusive of 0)",
                error_code="INVALID_CONFIDENCE_LEVEL",
            )

        with get_db_session() as session:
            try:
                # Check if test ID already exists
                existing_test = (
                    session.query(RuleABTest)
                    .filter(RuleABTest.test_id == test_id)
                    .first()
                )

                if existing_test:
                    raise DataValidationError(
                        f"Test with ID '{test_id}' already exists",
                        error_code="TEST_ID_EXISTS",
                        context={"test_id": test_id},
                    )

                # Calculate end time if duration is specified
                start_time = datetime.utcnow()
                end_time = None
                if duration_hours:
                    end_time = start_time + timedelta(hours=duration_hours)

                # Create test
                test = RuleABTest(
                    test_id=test_id,
                    test_name=test_name,
                    description=description,
                    rule_id=rule_id,
                    ruleset_id=ruleset_id,
                    traffic_split_a=traffic_split_a,
                    traffic_split_b=traffic_split_b,
                    variant_a_version=variant_a_version,
                    variant_b_version=variant_b_version,
                    variant_a_description=variant_a_description,
                    variant_b_description=variant_b_description,
                    status="draft",
                    start_time=start_time,
                    end_time=end_time,
                    duration_hours=duration_hours,
                    min_sample_size=min_sample_size,
                    confidence_level=confidence_level,
                    created_by=created_by,
                    tags=tags,
                    extra_metadata=metadata,
                )

                session.add(test)
                session.commit()

                logger.info(
                    "A/B test created",
                    test_id=test_id,
                    rule_id=rule_id,
                    variant_a=variant_a_version,
                    variant_b=variant_b_version,
                )

                return test.to_dict()

            except DataValidationError:
                session.rollback()
                raise
            except Exception as e:
                session.rollback()
                logger.error(
                    "Failed to create A/B test",
                    test_id=test_id,
                    error=str(e),
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to create A/B test: {str(e)}",
                    error_code="TEST_CREATE_ERROR",
                    context={"test_id": test_id, "error": str(e)},
                ) from e

    def start_test(
        self, test_id: str, started_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start an A/B test.

        Args:
            test_id: Test identifier
            started_by: User starting the test

        Returns:
            Updated test dictionary

        Raises:
            DataValidationError: If test not found or already started
            ConfigurationError: If start fails
        """
        with get_db_session() as session:
            try:
                test = (
                    session.query(RuleABTest)
                    .filter(RuleABTest.test_id == test_id)
                    .first()
                )

                if not test:
                    raise DataValidationError(
                        f"Test '{test_id}' not found",
                        error_code="TEST_NOT_FOUND",
                        context={"test_id": test_id},
                    )

                if test.status != "draft":
                    raise DataValidationError(
                        f"Test '{test_id}' is not in draft status (current: {test.status})",
                        error_code="TEST_NOT_DRAFT",
                        context={"test_id": test_id, "current_status": test.status},
                    )

                test.status = "running"
                test.start_time = datetime.utcnow()
                if test.duration_hours:
                    test.end_time = test.start_time + timedelta(
                        hours=test.duration_hours
                    )

                session.commit()

                logger.info(
                    "A/B test started", test_id=test_id, started_by=started_by
                )

                return test.to_dict()

            except DataValidationError:
                session.rollback()
                raise
            except Exception as e:
                session.rollback()
                logger.error(
                    "Failed to start A/B test",
                    test_id=test_id,
                    error=str(e),
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to start A/B test: {str(e)}",
                    error_code="TEST_START_ERROR",
                    context={"test_id": test_id, "error": str(e)},
                ) from e

    def stop_test(
        self,
        test_id: str,
        winning_variant: Optional[str] = None,
        stopped_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Stop an A/B test.

        Args:
            test_id: Test identifier
            winning_variant: Winning variant ('A' or 'B')
            stopped_by: User stopping the test

        Returns:
            Updated test dictionary

        Raises:
            DataValidationError: If test not found or not running
            ConfigurationError: If stop fails
        """
        with get_db_session() as session:
            try:
                test = (
                    session.query(RuleABTest)
                    .filter(RuleABTest.test_id == test_id)
                    .first()
                )

                if not test:
                    raise DataValidationError(
                        f"Test '{test_id}' not found",
                        error_code="TEST_NOT_FOUND",
                        context={"test_id": test_id},
                    )

                if test.status not in ["running", "draft"]:
                    raise DataValidationError(
                        f"Test '{test_id}' is not running or draft (current: {test.status})",
                        error_code="TEST_NOT_RUNNING",
                        context={
                            "test_id": test_id,
                            "current_status": test.status,
                        },
                    )

                if winning_variant and winning_variant not in ["A", "B"]:
                    raise DataValidationError(
                        f"Invalid winning variant: {winning_variant}. Must be 'A' or 'B'",
                        error_code="INVALID_WINNING_VARIANT",
                    )

                test.status = "completed"
                test.end_time = datetime.utcnow()
                test.winning_variant = winning_variant

                # Calculate statistical significance if both variants have data
                if winning_variant:
                    metrics = self.get_test_metrics(test_id)
                    test.statistical_significance = metrics.get(
                        "statistical_significance"
                    )

                session.commit()

                logger.info(
                    "A/B test stopped",
                    test_id=test_id,
                    winning_variant=winning_variant,
                    stopped_by=stopped_by,
                )

                return test.to_dict()

            except DataValidationError:
                session.rollback()
                raise
            except Exception as e:
                session.rollback()
                logger.error(
                    "Failed to stop A/B test",
                    test_id=test_id,
                    error=str(e),
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to stop A/B test: {str(e)}",
                    error_code="TEST_STOP_ERROR",
                    context={"test_id": test_id, "error": str(e)},
                ) from e

    def assign_variant(
        self,
        test_id: str,
        assignment_key: str,
        db_session: Optional[Session] = None,
    ) -> str:
        """
        Assign an assignment key to a variant using hash-based routing.

        This ensures consistent assignment for the same key.

        Args:
            test_id: Test identifier
            assignment_key: Key for assignment (user ID, session ID, etc.)
            db_session: Optional database session

        Returns:
            Assigned variant ('A' or 'B')

        Raises:
            DataValidationError: If test not found or not running
            ConfigurationError: If assignment fails
        """
        def _do_assign(sess: Session) -> str:
            # Check if already assigned
            assignment = (
                sess.query(TestAssignment)
                .filter(
                    TestAssignment.ab_test_id == RuleABTest.id,
                    RuleABTest.test_id == test_id,
                    TestAssignment.assignment_key == assignment_key,
                )
                .join(RuleABTest)
                .first()
            )

            if assignment:
                assignment.execution_count += 1
                assignment.last_execution_at = datetime.utcnow()
                sess.commit()
                logger.debug(
                    "Existing assignment found",
                    test_id=test_id,
                    assignment_key=assignment_key,
                    variant=assignment.variant,
                )
                return assignment.variant

            test = (
                sess.query(RuleABTest)
                .filter(RuleABTest.test_id == test_id)
                .first()
            )
            if not test:
                raise DataValidationError(
                    f"Test '{test_id}' not found",
                    error_code="TEST_NOT_FOUND",
                    context={"test_id": test_id},
                )
            if test.status != "running":
                raise DataValidationError(
                    f"Test '{test_id}' is not running (current: {test.status})",
                    error_code="TEST_NOT_RUNNING",
                    context={"test_id": test_id, "current_status": test.status},
                )

            hash_value = int(
                hashlib.md5(f"{test_id}:{assignment_key}".encode()).hexdigest(), 16
            )
            split_point = int(test.traffic_split_a * 100)
            variant = "A" if (hash_value % 100) < split_point else "B"

            assignment = TestAssignment(
                ab_test_id=test.id,
                assignment_key=assignment_key,
                variant=variant,
                assigned_at=datetime.utcnow(),
                execution_count=1,
                last_execution_at=datetime.utcnow(),
            )
            sess.add(assignment)
            sess.commit()
            logger.debug(
                "New assignment created",
                test_id=test_id,
                assignment_key=assignment_key,
                variant=variant,
            )
            return variant

        try:
            if db_session is not None:
                try:
                    return _do_assign(db_session)
                except DataValidationError:
                    raise
                except Exception:
                    db_session.rollback()
                    raise
            with get_db_session() as session:
                return _do_assign(session)
        except DataValidationError:
            raise
        except Exception as e:
            logger.error(
                "Failed to assign variant",
                test_id=test_id,
                assignment_key=assignment_key,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to assign variant: {str(e)}",
                error_code="ASSIGNMENT_ERROR",
                context={"test_id": test_id, "assignment_key": assignment_key},
            ) from e

    def get_test_metrics(self, test_id: str) -> Dict[str, Any]:
        """
        Get metrics for an A/B test.

        Args:
            test_id: Test identifier

        Returns:
            Dictionary with test metrics

        Raises:
            DataValidationError: If test not found
            ConfigurationError: If metrics retrieval fails
        """
        with get_db_session() as session:
            try:
                test = (
                    session.query(RuleABTest)
                    .filter(RuleABTest.test_id == test_id)
                    .first()
                )

                if not test:
                    raise DataValidationError(
                        f"Test '{test_id}' not found",
                        error_code="TEST_NOT_FOUND",
                        context={"test_id": test_id},
                    )

                # Get assignment counts
                assignment_counts = (
                    session.query(
                        TestAssignment.variant,
                        func.count(TestAssignment.id).label("count"),
                    )
                    .filter(TestAssignment.ab_test_id == test.id)
                    .group_by(TestAssignment.variant)
                    .all()
                )

                counts = {"A": 0, "B": 0}
                for variant, count in assignment_counts:
                    counts[variant] = count

                # Get execution logs for each variant
                variant_a_logs = (
                    session.query(ExecutionLog)
                    .filter(
                        ExecutionLog.ab_test_id == test.id,
                        ExecutionLog.ab_test_variant == "A",
                    )
                    .all()
                )

                variant_b_logs = (
                    session.query(ExecutionLog)
                    .filter(
                        ExecutionLog.ab_test_id == test.id,
                        ExecutionLog.ab_test_variant == "B",
                    )
                    .all()
                )

                # Calculate metrics for each variant
                def calculate_metrics(logs):
                    total_executions = len(logs)
                    successful_executions = sum(1 for log in logs if log.success)
                    avg_execution_time = (
                        sum(log.execution_time_ms for log in logs) / total_executions
                        if total_executions > 0
                        else 0
                    )
                    avg_total_points = (
                        sum(log.total_points or 0 for log in logs) / total_executions
                        if total_executions > 0
                        else 0
                    )

                    return {
                        "total_executions": total_executions,
                        "successful_executions": successful_executions,
                        "failed_executions": total_executions - successful_executions,
                        "success_rate": (
                            successful_executions / total_executions
                            if total_executions > 0
                            else 0
                        ),
                        "avg_execution_time_ms": avg_execution_time,
                        "avg_total_points": avg_total_points,
                    }

                variant_a_metrics = calculate_metrics(variant_a_logs)
                variant_b_metrics = calculate_metrics(variant_b_logs)

                # Calculate statistical significance using chi-square test
                statistical_significance = None
                if (
                    variant_a_metrics["successful_executions"] > 0
                    or variant_a_metrics["failed_executions"] > 0
                ) and (
                    variant_b_metrics["successful_executions"] > 0
                    or variant_b_metrics["failed_executions"] > 0
                ):
                    try:
                        import math

                        observed = [
                            variant_a_metrics["successful_executions"],
                            variant_a_metrics["failed_executions"],
                            variant_b_metrics["successful_executions"],
                            variant_b_metrics["failed_executions"],
                        ]

                        row_totals = [
                            sum(observed[:2]),
                            sum(observed[2:]),
                        ]
                        col_totals = [
                            observed[0] + observed[2],
                            observed[1] + observed[3],
                        ]
                        grand_total = sum(observed)

                        if grand_total > 0:
                            chi_square = 0
                            for i in range(4):
                                row_idx = i // 2
                                col_idx = i % 2
                                expected = (
                                    row_totals[row_idx] * col_totals[col_idx]
                                ) / grand_total
                                if expected > 0:
                                    chi_square += (
                                        (observed[i] - expected) ** 2
                                    ) / expected

                            # Approximate p-value (simplified)
                            if chi_square > 0:
                                p_value = math.exp(-chi_square / 2) / math.sqrt(
                                    2 * math.pi * chi_square
                                )
                                statistical_significance = 1 - p_value

                    except Exception:
                        # Statistical calculation failed, continue without it
                        pass

                result = {
                    "test_id": test_id,
                    "status": test.status,
                    "variant_a": {
                        "version": test.variant_a_version,
                        "description": test.variant_a_description,
                        "traffic_split": test.traffic_split_a,
                        "assignments": counts["A"],
                        "metrics": variant_a_metrics,
                    },
                    "variant_b": {
                        "version": test.variant_b_version,
                        "description": test.variant_b_description,
                        "traffic_split": test.traffic_split_b,
                        "assignments": counts["B"],
                        "metrics": variant_b_metrics,
                    },
                    "statistical_significance": statistical_significance,
                    "winning_variant": test.winning_variant,
                    "min_sample_size": test.min_sample_size,
                    "confidence_level": test.confidence_level,
                    "sample_size_met": (
                        counts["A"] >= (test.min_sample_size or 0)
                        and counts["B"] >= (test.min_sample_size or 0)
                    ),
                }

                logger.info(
                    "Test metrics retrieved",
                    test_id=test_id,
                    variant_a_assignments=counts["A"],
                    variant_b_assignments=counts["B"],
                )

                return result

            except DataValidationError:
                raise
            except Exception as e:
                logger.error(
                    "Failed to get test metrics",
                    test_id=test_id,
                    error=str(e),
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to get test metrics: {str(e)}",
                    error_code="METRICS_ERROR",
                    context={"test_id": test_id, "error": str(e)},
                ) from e

    def get_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an A/B test by ID.

        Args:
            test_id: Test identifier

        Returns:
            Test dictionary if found, None otherwise

        Raises:
            DataValidationError: If test_id is empty
        """
        if not test_id or not test_id.strip():
            raise DataValidationError(
                "Test ID cannot be empty", error_code="TEST_ID_EMPTY"
            )

        with get_db_session() as session:
            try:
                test = (
                    session.query(RuleABTest)
                    .filter(RuleABTest.test_id == test_id)
                    .first()
                )

                if not test:
                    logger.warning("Test not found", test_id=test_id)
                    return None

                logger.info("Test retrieved", test_id=test_id)

                return test.to_dict()

            except DataValidationError:
                raise
            except Exception as e:
                logger.error(
                    "Failed to get test",
                    test_id=test_id,
                    error=str(e),
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to get test: {str(e)}",
                    error_code="TEST_GET_ERROR",
                    context={"test_id": test_id, "error": str(e)},
                ) from e

    def list_tests(
        self,
        rule_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List A/B tests with optional filters.

        Args:
            rule_id: Optional rule ID filter
            status: Optional status filter
            limit: Maximum number of tests to return

        Returns:
            List of test dictionaries

        Raises:
            ConfigurationError: If listing fails
        """
        with get_db_session() as session:
            try:
                query = session.query(RuleABTest)

                if rule_id:
                    query = query.filter(RuleABTest.rule_id == rule_id)

                if status:
                    query = query.filter(RuleABTest.status == status)

                query = query.order_by(RuleABTest.created_at.desc())

                if limit:
                    query = query.limit(limit)

                tests = query.all()

                result = [t.to_dict() for t in tests]
                logger.info(
                    "Tests listed",
                    count=len(result),
                    rule_id=rule_id,
                    status=status,
                )

                return result

            except Exception as e:
                logger.error(
                    "Failed to list tests",
                    rule_id=rule_id,
                    status=status,
                    error=str(e),
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to list tests: {str(e)}",
                    error_code="TEST_LIST_ERROR",
                    context={
                        "rule_id": rule_id,
                        "status": status,
                        "error": str(e),
                    },
                ) from e

    def delete_test(self, test_id: str) -> None:
        """
        Delete an A/B test.

        Args:
            test_id: Test identifier

        Raises:
            DataValidationError: If test not found or not in draft status
            ConfigurationError: If deletion fails
        """
        with get_db_session() as session:
            try:
                test = (
                    session.query(RuleABTest)
                    .filter(RuleABTest.test_id == test_id)
                    .first()
                )

                if not test:
                    raise DataValidationError(
                        f"Test '{test_id}' not found",
                        error_code="TEST_NOT_FOUND",
                        context={"test_id": test_id},
                    )

                if test.status != "draft":
                    raise DataValidationError(
                        f"Cannot delete test '{test_id}' in status '{test.status}'. Only draft tests can be deleted.",
                        error_code="TEST_NOT_DRAFT",
                        context={
                            "test_id": test_id,
                            "current_status": test.status,
                        },
                    )

                session.delete(test)
                session.commit()

                logger.info("Test deleted", test_id=test_id)

            except DataValidationError:
                session.rollback()
                raise
            except Exception as e:
                session.rollback()
                logger.error(
                    "Failed to delete test",
                    test_id=test_id,
                    error=str(e),
                    exc_info=True,
                )
                raise ConfigurationError(
                    f"Failed to delete test: {str(e)}",
                    error_code="TEST_DELETE_ERROR",
                    context={"test_id": test_id, "error": str(e)},
                ) from e


# Global service instance
_ab_testing_service: Optional[ABTestingService] = None


def get_ab_testing_service() -> ABTestingService:
    """
    Get the global A/B testing service instance.

    Returns:
        ABTestingService instance
    """
    global _ab_testing_service
    if _ab_testing_service is None:
        _ab_testing_service = ABTestingService()
    return _ab_testing_service
