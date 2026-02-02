"""
Rule Registry for in-memory rule caching.

This module provides a thread-safe in-memory cache for rules
to support hot reload functionality.
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import threading
from collections import defaultdict

from common.logger import get_logger
from common.db_models import Rule, Ruleset

logger = get_logger(__name__)


class RuleRegistry:
    """
    Thread-safe in-memory registry for rules.

    This registry caches rules in memory to support fast rule execution
    and hot reload functionality. It provides:
    - Thread-safe read/write access
    - Version-aware rule tracking
    - Change notifications
    - Ruleset-level organization
    """

    def __init__(self):
        """Initialize rule registry."""
        self._lock = threading.RLock()
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._rulesets: Dict[int, Dict[str, Any]] = {}
        self._ruleset_rules: Dict[int, List[str]] = defaultdict(list)
        self._version: int = 0
        self._last_reload: Optional[datetime] = None
        self._subscribers: List[Callable[[str, Any], None]] = []
        self._rule_versions: Dict[str, List[int]] = defaultdict(list)

        logger.info("RuleRegistry initialized")

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a rule by ID.

        Args:
            rule_id: Rule identifier

        Returns:
            Rule dictionary if found, None otherwise
        """
        with self._lock:
            return self._rules.get(rule_id)

    def get_rules(self, ruleset_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all rules, optionally filtered by ruleset.

        Args:
            ruleset_id: Optional ruleset ID filter

        Returns:
            List of rule dictionaries
        """
        with self._lock:
            if ruleset_id:
                rule_ids = self._ruleset_rules.get(ruleset_id, [])
                return [self._rules[rid] for rid in rule_ids if rid in self._rules]
            return list(self._rules.values())

    def get_ruleset(self, ruleset_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a ruleset by ID.

        Args:
            ruleset_id: Ruleset identifier

        Returns:
            Ruleset dictionary if found, None otherwise
        """
        with self._lock:
            return self._rulesets.get(ruleset_id)

    def get_rulesets(self) -> List[Dict[str, Any]]:
        """
        Get all rulesets.

        Returns:
            List of ruleset dictionaries
        """
        with self._lock:
            return list(self._rulesets.values())

    def add_rule(self, rule: Rule) -> None:
        """
        Add or update a rule in the registry.

        Args:
            rule: Rule model instance
        """
        with self._lock:
            rule_dict = {
                "id": rule.id,
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "attribute": rule.attribute,
                "condition": rule.condition,
                "constant": rule.constant,
                "message": rule.message,
                "weight": rule.weight,
                "rule_point": rule.rule_point,
                "priority": rule.priority,
                "action_result": rule.action_result,
                "status": rule.status,
                "version": rule.version,
                "ruleset_id": rule.ruleset_id,
                "tags": rule.tags,
                "metadata": rule.extra_metadata,
                "cached_at": datetime.utcnow(),
            }

            # Track versions
            self._rule_versions[rule.rule_id].append(rule.id)

            self._rules[rule.rule_id] = rule_dict

            # Update ruleset index
            if rule.ruleset_id not in self._ruleset_rules[rule.ruleset_id]:
                self._ruleset_rules[rule.ruleset_id].append(rule.rule_id)

            self._version += 1

            # Notify subscribers
            self._notify("rule_added", rule_dict)

            logger.debug(
                "Rule added to registry",
                rule_id=rule.rule_id,
                version=self._version,
            )

    def update_rule(self, rule: Rule) -> None:
        """
        Update an existing rule in the registry.

        Args:
            rule: Rule model instance
        """
        with self._lock:
            if rule.rule_id not in self._rules:
                logger.warning(
                    "Rule not found in registry for update",
                    rule_id=rule.rule_id,
                )
                self.add_rule(rule)
                return

            rule_dict = {
                "id": rule.id,
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "attribute": rule.attribute,
                "condition": rule.condition,
                "constant": rule.constant,
                "message": rule.message,
                "weight": rule.weight,
                "rule_point": rule.rule_point,
                "priority": rule.priority,
                "action_result": rule.action_result,
                "status": rule.status,
                "version": rule.version,
                "ruleset_id": rule.ruleset_id,
                "tags": rule.tags,
                "metadata": rule.extra_metadata,
                "cached_at": datetime.utcnow(),
            }

            old_rule = self._rules[rule.rule_id]
            self._rules[rule.rule_id] = rule_dict
            self._version += 1

            # Notify subscribers
            self._notify("rule_updated", {"old": old_rule, "new": rule_dict})

            logger.debug(
                "Rule updated in registry",
                rule_id=rule.rule_id,
                version=self._version,
            )

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule from the registry.

        Args:
            rule_id: Rule identifier

        Returns:
            True if rule was removed, False if not found
        """
        with self._lock:
            if rule_id not in self._rules:
                logger.warning(
                    "Rule not found in registry for removal", rule_id=rule_id
                )
                return False

            rule = self._rules.pop(rule_id)
            ruleset_id = rule.get("ruleset_id")

            # Remove from ruleset index
            if ruleset_id and ruleset_id in self._ruleset_rules:
                if rule_id in self._ruleset_rules[ruleset_id]:
                    self._ruleset_rules[ruleset_id].remove(rule_id)

            self._version += 1

            # Notify subscribers
            self._notify("rule_removed", rule)

            logger.debug(
                "Rule removed from registry",
                rule_id=rule_id,
                version=self._version,
            )

            return True

    def add_ruleset(self, ruleset: Ruleset) -> None:
        """
        Add or update a ruleset in the registry.

        Args:
            ruleset: Ruleset model instance
        """
        with self._lock:
            ruleset_dict = {
                "id": ruleset.id,
                "name": ruleset.name,
                "description": ruleset.description,
                "version": ruleset.version,
                "status": ruleset.status,
                "tenant_id": ruleset.tenant_id,
                "is_default": ruleset.is_default,
                "tags": ruleset.tags,
                "metadata": ruleset.extra_metadata,
                "cached_at": datetime.utcnow(),
            }

            self._rulesets[ruleset.id] = ruleset_dict
            self._version += 1

            # Notify subscribers
            self._notify("ruleset_added", ruleset_dict)

            logger.debug(
                "Ruleset added to registry",
                ruleset_id=ruleset.id,
                version=self._version,
            )

    def remove_ruleset(self, ruleset_id: int) -> bool:
        """
        Remove a ruleset and all its rules from the registry.

        Args:
            ruleset_id: Ruleset identifier

        Returns:
            True if ruleset was removed, False if not found
        """
        with self._lock:
            if ruleset_id not in self._rulesets:
                logger.warning(
                    "Ruleset not found in registry for removal",
                    ruleset_id=ruleset_id,
                )
                return False

            # Remove all rules in the ruleset
            rule_ids = self._ruleset_rules.get(ruleset_id, [])
            for rule_id in rule_ids:
                if rule_id in self._rules:
                    self._rules.pop(rule_id)

            # Remove ruleset and index
            self._rulesets.pop(ruleset_id)
            self._ruleset_rules.pop(ruleset_id, None)

            self._version += 1

            # Notify subscribers
            self._notify("ruleset_removed", {"ruleset_id": ruleset_id})

            logger.debug(
                "Ruleset removed from registry",
                ruleset_id=ruleset_id,
                version=self._version,
            )

            return True

    def clear(self) -> None:
        """Clear all rules and rulesets from the registry."""
        with self._lock:
            self._rules.clear()
            self._rulesets.clear()
            self._ruleset_rules.clear()
            self._rule_versions.clear()
            self._version = 0
            self._last_reload = None

            # Notify subscribers
            self._notify("registry_cleared", {})

            logger.info("Registry cleared")

    def get_version(self) -> int:
        """
        Get the current registry version.

        Returns:
            Current version number
        """
        with self._lock:
            return self._version

    def get_last_reload(self) -> Optional[datetime]:
        """
        Get the last reload timestamp.

        Returns:
            Last reload datetime or None
        """
        with self._lock:
            return self._last_reload

    def set_last_reload(self, timestamp: datetime) -> None:
        """
        Set the last reload timestamp.

        Args:
            timestamp: Reload timestamp
        """
        with self._lock:
            self._last_reload = timestamp

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            return {
                "rule_count": len(self._rules),
                "ruleset_count": len(self._rulesets),
                "version": self._version,
                "last_reload": self._last_reload.isoformat()
                if self._last_reload
                else None,
                "subscriber_count": len(self._subscribers),
            }

    def subscribe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to registry change notifications.

        Args:
            callback: Function to call on registry changes
                      Receives (event_type, data) arguments
        """
        with self._lock:
            self._subscribers.append(callback)
            logger.debug("Subscriber added to registry")

    def unsubscribe(self, callback: Callable[[str, Any], None]) -> None:
        """
        Unsubscribe from registry change notifications.

        Args:
            callback: Function to remove from subscribers
        """
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
                logger.debug("Subscriber removed from registry")

    def _notify(self, event_type: str, data: Any) -> None:
        """
        Notify all subscribers of a change.

        Args:
            event_type: Type of event (rule_added, rule_updated, etc.)
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


# Global registry instance
_rule_registry: Optional[RuleRegistry] = None


def get_rule_registry() -> RuleRegistry:
    """
    Get the global rule registry instance.

    Returns:
        RuleRegistry instance
    """
    global _rule_registry
    if _rule_registry is None:
        _rule_registry = RuleRegistry()
    return _rule_registry
