"""
Hot Reload Service for Rules.

This module provides functionality to monitor and reload rules
in real-time without restarting the application.
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
import threading
import time

from sqlalchemy.orm import Session

from common.logger import get_logger
from common.exceptions import ConfigurationError, DataValidationError
from common.db_models import Rule, Ruleset, RuleStatus
from common.db_connection import get_db_session
from common.rule_registry import get_rule_registry
from common.rule_validator import validate_rule
from common.metrics import get_metrics

logger = get_logger(__name__)


class HotReloadService:
    """
    Service for hot reloading rules.

    This service monitors database for rule changes and reloads
    rules in memory without restarting the application.
    """

    def __init__(
        self,
        auto_reload_enabled: bool = True,
        reload_interval_seconds: int = 30,
        validation_enabled: bool = True,
    ):
        """
        Initialize hot reload service.

        Args:
            auto_reload_enabled: Enable automatic reloading
            reload_interval_seconds: Interval for checking changes (seconds)
            validation_enabled: Validate rules before reloading
        """
        self._registry = get_rule_registry()
        self._auto_reload_enabled = auto_reload_enabled
        self._reload_interval_seconds = reload_interval_seconds
        self._validation_enabled = validation_enabled

        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reload_lock = threading.RLock()

        self._last_check_time: Optional[datetime] = None
        self._last_known_rule_ids: set = set()
        self._reload_count: int = 0
        self._last_reload_time: Optional[datetime] = None
        self._last_reload_status: str = "success"
        self._last_reload_error: Optional[str] = None

        self._subscribers: List[Callable[[str, Dict[str, Any]], None]] = []

        logger.info(
            "HotReloadService initialized",
            auto_reload=auto_reload_enabled,
            reload_interval=reload_interval_seconds,
            validation=validation_enabled,
        )

    def start(self) -> None:
        """Start the hot reload monitoring thread."""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("Hot reload monitoring already running")
            return

        self._stop_event.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="HotReloadMonitor"
        )
        self._monitoring_thread.start()

        logger.info("Hot reload monitoring started")

    def stop(self) -> None:
        """Stop the hot reload monitoring thread."""
        if not self._monitoring_thread or not self._monitoring_thread.is_alive():
            logger.warning("Hot reload monitoring not running")
            return

        self._stop_event.set()
        self._monitoring_thread.join(timeout=5)

        logger.info("Hot reload monitoring stopped")

    def reload_rules(
        self,
        ruleset_id: Optional[int] = None,
        rule_id: Optional[str] = None,
        force: bool = False,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Reload rules from database into registry.

        Args:
            ruleset_id: Optional ruleset ID to reload
            rule_id: Optional rule ID to reload
            force: Force reload even if no changes detected
            validate: Validate rules before reloading

        Returns:
            Reload result dictionary

        Raises:
            ConfigurationError: If reload fails
        """
        with self._reload_lock:
            start_time = datetime.utcnow()

            try:
                session = get_db_session()

                # Determine what to reload
                query = session.query(Rule).filter(
                    Rule.status == RuleStatus.ACTIVE.value
                )

                if rule_id:
                    query = query.filter(Rule.rule_id == rule_id)
                elif ruleset_id:
                    query = query.filter(Rule.ruleset_id == ruleset_id)

                rules = query.all()

                # Load rulesets
                ruleset_query = session.query(Ruleset).filter(
                    Ruleset.status == RuleStatus.ACTIVE.value
                )

                if ruleset_id:
                    ruleset_query = ruleset_query.filter(Ruleset.id == ruleset_id)

                rulesets = ruleset_query.all()

                # Validate rules if enabled
                if validate and self._validation_enabled:
                    validation_errors = []
                    for rule in rules:
                        rule_dict = rule.to_dict()
                        try:
                            validate_rule(rule_dict)
                        except Exception as e:
                            validation_errors.append(
                                {"rule_id": rule.rule_id, "error": str(e)}
                            )

                    if validation_errors:
                        raise ConfigurationError(
                            "Rule validation failed",
                            error_code="VALIDATION_ERROR",
                            context={"validation_errors": validation_errors},
                        )

                # Clear existing data if full reload
                if not rule_id and not ruleset_id:
                    self._registry.clear()

                # Load rulesets
                for ruleset in rulesets:
                    self._registry.add_ruleset(ruleset)

                # Load rules
                for rule in rules:
                    self._registry.add_rule(rule)

                # Update registry metadata
                self._registry.set_last_reload(start_time)

                # Track metrics
                reload_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                metrics = get_metrics()
                metrics.increment("rule_reloads", value=1)
                metrics.put_metric("rule_reload_time", reload_time_ms, "Milliseconds")
                metrics.put_metric("rules_reloaded", len(rules), "Count")

                # Update reload statistics
                self._reload_count += 1
                self._last_reload_time = start_time
                self._last_reload_status = "success"
                self._last_reload_error = None

                result = {
                    "status": "success",
                    "timestamp": start_time.isoformat(),
                    "reload_time_ms": reload_time_ms,
                    "rules_loaded": len(rules),
                    "rulesets_loaded": len(rulesets),
                    "reload_count": self._reload_count,
                    "filtered_by": {
                        "ruleset_id": ruleset_id,
                        "rule_id": rule_id,
                    },
                }

                # Notify subscribers
                self._notify("rules_reloaded", result)

                logger.info(
                    "Rules reloaded successfully",
                    rules_count=len(rules),
                    rulesets_count=len(rulesets),
                    reload_time_ms=reload_time_ms,
                    ruleset_id=ruleset_id,
                    rule_id=rule_id,
                )

                return result

            except Exception as e:
                self._last_reload_status = "error"
                self._last_reload_error = str(e)

                logger.error(
                    "Failed to reload rules",
                    error=str(e),
                    exc_info=True,
                    ruleset_id=ruleset_id,
                    rule_id=rule_id,
                )

                raise ConfigurationError(
                    f"Failed to reload rules: {str(e)}",
                    error_code="RELOAD_ERROR",
                    context={"error": str(e)},
                ) from e

    def reload_single_rule(self, rule_id: str) -> Dict[str, Any]:
        """
        Reload a single rule.

        Args:
            rule_id: Rule identifier

        Returns:
            Reload result dictionary

        Raises:
            DataValidationError: If rule not found
            ConfigurationError: If reload fails
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty", error_code="RULE_ID_EMPTY"
            )

        return self.reload_rules(rule_id=rule_id, validate=True)

    def reload_ruleset(self, ruleset_id: int) -> Dict[str, Any]:
        """
        Reload all rules in a ruleset.

        Args:
            ruleset_id: Ruleset identifier

        Returns:
            Reload result dictionary

        Raises:
            ConfigurationError: If reload fails
        """
        if ruleset_id < 1:
            raise DataValidationError(
                "Invalid ruleset ID", error_code="INVALID_RULESET_ID"
            )

        return self.reload_rules(ruleset_id=ruleset_id, validate=True)

    def validate_reload(self) -> Dict[str, Any]:
        """
        Validate the current rule configuration.

        Args:
            None

        Returns:
            Validation result dictionary
        """
        start_time = datetime.utcnow()

        try:
            rules = self._registry.get_rules()

            validation_errors = []
            for rule in rules:
                try:
                    validate_rule(rule)
                except Exception as e:
                    validation_errors.append(
                        {"rule_id": rule.get("rule_id"), "error": str(e)}
                    )

            validation_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "total_rules": len(rules),
                "valid_rules": len(rules) - len(validation_errors),
                "validation_time_ms": validation_time_ms,
                "timestamp": start_time.isoformat(),
            }

            logger.info(
                "Validation completed",
                valid=result["valid"],
                errors_count=len(validation_errors),
                validation_time_ms=validation_time_ms,
            )

            return result

        except Exception as e:
            logger.error("Failed to validate rules", error=str(e), exc_info=True)

            return {
                "valid": False,
                "errors": [{"error": str(e)}],
                "total_rules": 0,
                "valid_rules": 0,
                "validation_time_ms": 0,
                "timestamp": start_time.isoformat(),
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get hot reload service status.

        Returns:
            Status dictionary
        """
        registry_stats = self._registry.get_stats()

        return {
            "monitoring_active": self._monitoring_thread
            and self._monitoring_thread.is_alive(),
            "auto_reload_enabled": self._auto_reload_enabled,
            "reload_interval_seconds": self._reload_interval_seconds,
            "validation_enabled": self._validation_enabled,
            "last_check_time": self._last_check_time.isoformat()
            if self._last_check_time
            else None,
            "last_reload_time": self._last_reload_time.isoformat()
            if self._last_reload_time
            else None,
            "last_reload_status": self._last_reload_status,
            "last_reload_error": self._last_reload_error,
            "reload_count": self._reload_count,
            "registry": registry_stats,
        }

    def get_reload_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get reload history.

        Args:
            limit: Maximum number of reloads to return

        Returns:
            List of reload events (simplified for now)
        """
        return [
            {
                "reload_count": self._reload_count,
                "last_reload_time": self._last_reload_time.isoformat()
                if self._last_reload_time
                else None,
                "status": self._last_reload_status,
                "error": self._last_reload_error,
            }
        ]

    def subscribe(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Subscribe to reload notifications.

        Args:
            callback: Function to call on reload events
        """
        self._subscribers.append(callback)
        logger.debug("Subscriber added to HotReloadService")

    def unsubscribe(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Unsubscribe from reload notifications.

        Args:
            callback: Function to remove from subscribers
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            logger.debug("Subscriber removed from HotReloadService")

    def _notify(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Notify all subscribers of an event.

        Args:
            event_type: Type of event
            data: Event data
        """
        for callback in self._subscribers:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(
                    "Error in subscriber callback",
                    event_type=event_type,
                    error=str(e),
                    exc_info=True,
                )

    def _monitor_loop(self) -> None:
        """
        Main monitoring loop.

        Periodically checks for rule changes and triggers reloads.
        """
        logger.info("Hot reload monitoring loop started")

        while not self._stop_event.is_set():
            try:
                self._check_for_changes()

                # Wait for next check
                self._stop_event.wait(self._reload_interval_seconds)

            except Exception as e:
                logger.error(
                    "Error in hot reload monitoring loop",
                    error=str(e),
                    exc_info=True,
                )
                # Continue monitoring despite errors
                self._stop_event.wait(5)

        logger.info("Hot reload monitoring loop stopped")

    def _check_for_changes(self) -> None:
        """
        Check for rule changes in the database.

        If changes are detected, triggers a reload.
        """
        self._last_check_time = datetime.utcnow()

        if not self._auto_reload_enabled:
            return

        try:
            session = get_db_session()

            # Get current rule IDs
            current_rule_ids = set(
                row[0]
                for row in session.query(Rule.rule_id)
                .filter(Rule.status == RuleStatus.ACTIVE.value)
                .all()
            )

            # Check for changes
            if current_rule_ids != self._last_known_rule_ids:
                logger.info(
                    "Rule changes detected",
                    previous_count=len(self._last_known_rule_ids),
                    current_count=len(current_rule_ids),
                )

                # Trigger reload
                try:
                    self.reload_rules(force=True, validate=True)
                except Exception as e:
                    logger.error(
                        "Failed to reload rules after change detection",
                        error=str(e),
                        exc_info=True,
                    )

                # Update known rule IDs
                self._last_known_rule_ids = current_rule_ids
            else:
                logger.debug("No rule changes detected")

        except Exception as e:
            logger.error(
                "Error checking for rule changes",
                error=str(e),
                exc_info=True,
            )


# Global service instance
_hot_reload_service: Optional[HotReloadService] = None


def get_hot_reload_service() -> HotReloadService:
    """
    Get global hot reload service instance.

    Returns:
        HotReloadService instance
    """
    global _hot_reload_service
    if _hot_reload_service is None:
        _hot_reload_service = HotReloadService()
    return _hot_reload_service
