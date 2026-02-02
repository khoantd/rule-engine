"""
Hot Reload Integration for Rule Execution.

This module provides utilities to integrate hot reload functionality
into rule execution flow.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from common.logger import get_logger
from common.rule_registry import get_rule_registry
from common.rule_engine_util import rule_run

logger = get_logger(__name__)


def get_rules_from_registry(
    ruleset_id: Optional[int] = None,
    rule_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Get rules from the registry for execution.

    Args:
        ruleset_id: Optional ruleset ID to filter by
        rule_ids: Optional list of rule IDs to retrieve

    Returns:
        List of rule dictionaries

    Raises:
        Exception: If retrieval fails
    """
    try:
        registry = get_rule_registry()

        # Get rules based on filters
        if rule_ids:
            # Get specific rules
            rules = []
            for rule_id in rule_ids:
                rule = registry.get_rule(rule_id)
                if rule:
                    rules.append(rule)
            return rules
        else:
            # Get all rules or ruleset rules
            return registry.get_rules(ruleset_id=ruleset_id)

    except Exception as e:
        logger.error(
            "Failed to get rules from registry",
            ruleset_id=ruleset_id,
            rule_ids=rule_ids,
            error=str(e),
            exc_info=True,
        )
        raise


def get_ruleset_from_registry(ruleset_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a ruleset from the registry.

    Args:
        ruleset_id: Ruleset identifier

    Returns:
        Ruleset dictionary or None if not found

    Raises:
        Exception: If retrieval fails
    """
    try:
        registry = get_rule_registry()
        return registry.get_ruleset(ruleset_id)

    except Exception as e:
        logger.error(
            "Failed to get ruleset from registry",
            ruleset_id=ruleset_id,
            error=str(e),
            exc_info=True,
        )
        raise


def execute_rules_from_registry(
    data: Dict[str, Any],
    ruleset_id: Optional[int] = None,
    rule_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Execute rules from the registry.

    Args:
        data: Input data for rule evaluation
        ruleset_id: Optional ruleset ID to execute
        rule_ids: Optional list of rule IDs to execute

    Returns:
        Dictionary containing:
            - total_points: Sum of rule points (weighted)
            - pattern_result: Concatenated action results
            - action_recommendation: Recommended action based on pattern
            - rules_executed: Number of rules executed
            - rules_matched: Number of rules that matched
            - execution_time_ms: Execution time in milliseconds
            - registry_version: Registry version at time of execution

    Raises:
        Exception: If execution fails
    """
    start_time = datetime.utcnow()

    try:
        # Get rules from registry
        rules = get_rules_from_registry(ruleset_id=ruleset_id, rule_ids=rule_ids)

        if not rules:
            logger.warning(
                "No rules found in registry", ruleset_id=ruleset_id, rule_ids=rule_ids
            )
            return {
                "total_points": 0.0,
                "pattern_result": "",
                "action_recommendation": None,
                "rules_executed": 0,
                "rules_matched": 0,
                "execution_time_ms": 0.0,
                "registry_version": get_rule_registry().get_version(),
            }

        # Execute each rule
        results = []
        total_points = 0.0
        matched_count = 0

        for rule in rules:
            try:
                result = rule_run(rule, data)

                # Calculate weighted points
                rule_point = float(result.get("rule_point", 0))
                weight = float(result.get("weight", 1.0))
                total_points += rule_point * weight

                # Track matches
                action_result = result.get("action_result", "-")
                if action_result != "-":
                    matched_count += 1

                results.append(action_result)

            except Exception as e:
                logger.error(
                    "Error executing rule",
                    rule_id=rule.get("rule_id"),
                    error=str(e),
                    exc_info=True,
                )
                continue

        # Build pattern result
        pattern_result = "".join(results) if results else ""

        # Get action recommendation
        action_recommendation = None
        if pattern_result:
            try:
                from common.rule_engine_util import find_action_recommendation
                from common.rule_engine_util import actions_set_cfg_read

                actions_set = actions_set_cfg_read()
                action_recommendation = find_action_recommendation(
                    actions_set, pattern_result
                )
            except Exception as e:
                logger.warning("Failed to get action recommendation", error=str(e))

        # Calculate execution time
        execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        result = {
            "total_points": total_points,
            "pattern_result": pattern_result,
            "action_recommendation": action_recommendation,
            "rules_executed": len(rules),
            "rules_matched": matched_count,
            "execution_time_ms": execution_time_ms,
            "registry_version": get_rule_registry().get_version(),
        }

        logger.info(
            "Rules executed from registry",
            rules_executed=len(rules),
            rules_matched=matched_count,
            total_points=total_points,
            execution_time_ms=execution_time_ms,
            registry_version=result["registry_version"],
        )

        return result

    except Exception as e:
        logger.error(
            "Failed to execute rules from registry",
            error=str(e),
            exc_info=True,
        )
        raise


def validate_registry_rules() -> Dict[str, Any]:
    """
    Validate all rules in the registry.

    Args:
        None

    Returns:
        Validation result dictionary with:
            - valid: Whether all rules are valid
            - total_rules: Total number of rules
            - valid_rules: Number of valid rules
            - invalid_rules: Number of invalid rules
            - errors: List of validation errors
            - validation_time_ms: Validation time in milliseconds

    Raises:
        Exception: If validation fails
    """
    start_time = datetime.utcnow()

    try:
        from common.rule_validator import validate_rule

        registry = get_rule_registry()
        rules = registry.get_rules()

        errors = []
        valid_count = 0

        for rule in rules:
            try:
                validate_rule(rule)
                valid_count += 1
            except Exception as e:
                errors.append(
                    {
                        "rule_id": rule.get("rule_id"),
                        "error": str(e),
                    }
                )

        validation_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        result = {
            "valid": len(errors) == 0,
            "total_rules": len(rules),
            "valid_rules": valid_count,
            "invalid_rules": len(errors),
            "errors": errors,
            "validation_time_ms": validation_time_ms,
        }

        logger.info(
            "Registry validation completed",
            valid=result["valid"],
            total_rules=len(rules),
            invalid_rules=len(errors),
            validation_time_ms=validation_time_ms,
        )

        return result

    except Exception as e:
        logger.error(
            "Failed to validate registry rules",
            error=str(e),
            exc_info=True,
        )
        raise


def get_registry_info() -> Dict[str, Any]:
    """
    Get information about the rule registry.

    Args:
        None

    Returns:
        Registry information dictionary with:
            - version: Current registry version
            - last_reload: Last reload timestamp
            - rule_count: Number of rules in registry
            - ruleset_count: Number of rulesets in registry

    Raises:
        Exception: If retrieval fails
    """
    try:
        registry = get_rule_registry()
        stats = registry.get_stats()

        return {
            "version": stats["version"],
            "last_reload": stats["last_reload"],
            "rule_count": stats["rule_count"],
            "ruleset_count": stats["ruleset_count"],
        }

    except Exception as e:
        logger.error(
            "Failed to get registry info",
            error=str(e),
            exc_info=True,
        )
        raise


def is_registry_fresh(max_age_seconds: int = 300) -> bool:
    """
    Check if the registry is fresh (recently reloaded).

    Args:
        max_age_seconds: Maximum age in seconds for registry to be considered fresh

    Returns:
        True if registry is fresh, False otherwise
    """
    try:
        registry = get_rule_registry()
        last_reload = registry.get_last_reload()

        if not last_reload:
            return False

        age = (datetime.utcnow() - last_reload).total_seconds()
        return age < max_age_seconds

    except Exception as e:
        logger.error(
            "Failed to check registry freshness",
            error=str(e),
            exc_info=True,
        )
        return False
