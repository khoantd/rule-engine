"""
Rule Validation API Module.

This module provides comprehensive rule validation capabilities including:
- Rule syntax validation
- Rule structure validation
- Rule dependency validation
- Condition validation
"""

import rule_engine
from typing import Any, Dict, List, Optional, Tuple
from common.logger import get_logger
from common.exceptions import RuleCompilationError, ConfigurationError, RuleValidationError
from common.rule_engine_util import conditions_set_load, rule_prepare

logger = get_logger(__name__)


class RuleValidationResult:
    """Result of rule validation containing validation status and errors."""
    
    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize validation result.
        
        Args:
            is_valid: Whether the rule is valid
            errors: List of validation errors
            warnings: List of validation warnings
        """
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
    
    def __bool__(self) -> bool:
        """Return True if validation passed."""
        return self.is_valid


class RuleValidator:
    """Validator for rule syntax and structure."""
    
    def __init__(self):
        """Initialize rule validator."""
        self._conditions_set: Optional[List[Any]] = None
    
    def _get_conditions_set(self) -> List[Any]:
        """Get conditions set, loading if necessary."""
        if self._conditions_set is None:
            try:
                self._conditions_set = conditions_set_load()
            except Exception as e:
                logger.warning("Failed to load conditions set for validation", error=str(e))
                self._conditions_set = []
        return self._conditions_set
    
    def validate_rule_structure(self, rule: Dict[str, Any]) -> RuleValidationResult:
        """
        Validate rule structure and required fields.
        
        Args:
            rule: Rule dictionary to validate
            
        Returns:
            RuleValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Check if rule is a dictionary
        if not isinstance(rule, dict):
            errors.append({
                'field': 'rule',
                'error': 'Rule must be a dictionary',
                'severity': 'error'
            })
            return RuleValidationResult(False, errors, warnings)
        
        # Required fields for all rules
        required_fields = ['rulename', 'type', 'priority', 'conditions']
        for field in required_fields:
            if field not in rule:
                errors.append({
                    'field': field,
                    'error': f"Required field '{field}' is missing",
                    'severity': 'error'
                })
        
        # Validate rule type
        if 'type' in rule:
            rule_type = rule['type']
            if rule_type not in ['simple', 'complex']:
                errors.append({
                    'field': 'type',
                    'error': f"Invalid rule type: '{rule_type}'. Must be 'simple' or 'complex'",
                    'severity': 'error'
                })
            else:
                # Validate type-specific fields
                if rule_type == 'simple':
                    if 'conditions' in rule and isinstance(rule['conditions'], dict):
                        if 'item' not in rule['conditions']:
                            errors.append({
                                'field': 'conditions.item',
                                'error': "Simple rule must have 'conditions.item'",
                                'severity': 'error'
                            })
                elif rule_type == 'complex':
                    if 'conditions' in rule and isinstance(rule['conditions'], dict):
                        if 'items' not in rule['conditions']:
                            errors.append({
                                'field': 'conditions.items',
                                'error': "Complex rule must have 'conditions.items' list",
                                'severity': 'error'
                            })
                        elif not isinstance(rule['conditions']['items'], list) or len(rule['conditions']['items']) == 0:
                            errors.append({
                                'field': 'conditions.items',
                                'error': "Complex rule must have at least one condition item",
                                'severity': 'error'
                            })
                        if 'mode' not in rule['conditions']:
                            errors.append({
                                'field': 'conditions.mode',
                                'error': "Complex rule must have 'conditions.mode'",
                                'severity': 'error'
                            })
        
        # Validate priority
        if 'priority' in rule:
            try:
                priority = int(rule['priority'])
                if priority < 0:
                    warnings.append({
                        'field': 'priority',
                        'warning': 'Priority should be non-negative',
                        'severity': 'warning'
                    })
            except (ValueError, TypeError):
                errors.append({
                    'field': 'priority',
                    'error': 'Priority must be an integer',
                    'severity': 'error'
                })
        
        # Validate rule_point
        if 'rulepoint' in rule or 'rule_point' in rule:
            rule_point = rule.get('rulepoint') or rule.get('rule_point')
            try:
                float(rule_point)
            except (ValueError, TypeError):
                errors.append({
                    'field': 'rulepoint',
                    'error': 'Rule point must be a number',
                    'severity': 'error'
                })
        
        # Validate weight
        if 'weight' in rule:
            try:
                weight = float(rule['weight'])
                if weight < 0:
                    warnings.append({
                        'field': 'weight',
                        'warning': 'Weight should be non-negative',
                        'severity': 'warning'
                    })
            except (ValueError, TypeError):
                errors.append({
                    'field': 'weight',
                    'error': 'Weight must be a number',
                    'severity': 'error'
                })
        
        # Validate action_result
        if 'action_result' in rule:
            if not isinstance(rule['action_result'], str):
                warnings.append({
                    'field': 'action_result',
                    'warning': 'Action result should be a string',
                    'severity': 'warning'
                })
        
        return RuleValidationResult(len(errors) == 0, errors, warnings)
    
    def validate_rule_condition(self, rule: Dict[str, Any]) -> RuleValidationResult:
        """
        Validate rule condition syntax and references.
        
        Args:
            rule: Rule dictionary to validate
            
        Returns:
            RuleValidationResult with validation status
        """
        errors = []
        warnings = []
        
        if not isinstance(rule, dict) or 'type' not in rule:
            return RuleValidationResult(False, [{
                'field': 'rule',
                'error': 'Invalid rule structure',
                'severity': 'error'
            }])
        
        rule_type = rule.get('type')
        conditions_set = self._get_conditions_set()
        
        try:
            if rule_type == 'simple':
                if 'conditions' in rule and isinstance(rule['conditions'], dict):
                    condition_id = rule['conditions'].get('item')
                    if condition_id:
                        # Check if condition exists
                        condition_found = any(
                            cond.condition_id == condition_id for cond in conditions_set
                        )
                        if not condition_found:
                            errors.append({
                                'field': 'conditions.item',
                                'error': f"Condition '{condition_id}' not found in conditions set",
                                'severity': 'error',
                                'condition_id': condition_id
                            })
            
            elif rule_type == 'complex':
                if 'conditions' in rule and isinstance(rule['conditions'], dict):
                    condition_items = rule['conditions'].get('items', [])
                    if isinstance(condition_items, list):
                        # Check each condition
                        for condition_id in condition_items:
                            condition_found = any(
                                cond.condition_id == condition_id for cond in conditions_set
                            )
                            if not condition_found:
                                errors.append({
                                    'field': 'conditions.items',
                                    'error': f"Condition '{condition_id}' not found in conditions set",
                                    'severity': 'error',
                                    'condition_id': condition_id
                                })
                        
                        # Validate mode for complex rules
                        mode = rule['conditions'].get('mode')
                        if mode and mode not in ['and', 'or']:
                            warnings.append({
                                'field': 'conditions.mode',
                                'warning': f"Mode '{mode}' may not be standard. Use 'and' or 'or'",
                                'severity': 'warning',
                                'mode': mode
                            })
        except Exception as e:
            errors.append({
                'field': 'conditions',
                'error': f"Error validating conditions: {str(e)}",
                'severity': 'error'
            })
        
        return RuleValidationResult(len(errors) == 0, errors, warnings)
    
    def validate_rule_syntax(self, rule: Dict[str, Any]) -> RuleValidationResult:
        """
        Validate rule syntax by attempting to compile the condition.
        
        Args:
            rule: Rule dictionary to validate
            
        Returns:
            RuleValidationResult with validation status
        """
        errors = []
        warnings = []
        
        try:
            # Try to prepare the rule to get the condition string
            conditions_set = self._get_conditions_set()
            prepared_rule = rule_prepare(conditions_set, rule)
            condition_str = prepared_rule.get('condition', '')
            
            if not condition_str:
                errors.append({
                    'field': 'condition',
                    'error': 'Failed to build condition string',
                    'severity': 'error'
                })
                return RuleValidationResult(False, errors, warnings)
            
            # Try to compile the condition using rule engine
            try:
                rule_engine.Rule(condition_str)
            except (rule_engine.errors.RuleSyntaxError, rule_engine.errors.SyntaxError) as e:
                errors.append({
                    'field': 'condition',
                    'error': f"Invalid condition syntax: {str(e)}",
                    'severity': 'error',
                    'condition': condition_str,
                    'rule_engine_error': str(e)
                })
            except Exception as e:
                errors.append({
                    'field': 'condition',
                    'error': f"Error compiling condition: {str(e)}",
                    'severity': 'error',
                    'condition': condition_str
                })
        
        except RuleCompilationError as e:
            errors.append({
                'field': 'rule',
                'error': f"Rule compilation failed: {str(e)}",
                'severity': 'error',
                'compilation_error': str(e)
            })
        except ConfigurationError as e:
            errors.append({
                'field': 'conditions',
                'error': f"Configuration error: {str(e)}",
                'severity': 'error',
                'configuration_error': str(e)
            })
        except Exception as e:
            errors.append({
                'field': 'rule',
                'error': f"Unexpected error during validation: {str(e)}",
                'severity': 'error'
            })
        
        return RuleValidationResult(len(errors) == 0, errors, warnings)
    
    def validate_rule(
        self,
        rule: Dict[str, Any],
        validate_structure: bool = True,
        validate_condition: bool = True,
        validate_syntax: bool = True
    ) -> RuleValidationResult:
        """
        Perform comprehensive rule validation.
        
        Args:
            rule: Rule dictionary to validate
            validate_structure: Whether to validate rule structure
            validate_condition: Whether to validate condition references
            validate_syntax: Whether to validate condition syntax
            
        Returns:
            RuleValidationResult with combined validation status
        """
        all_errors = []
        all_warnings = []
        
        # Validate structure
        if validate_structure:
            structure_result = self.validate_rule_structure(rule)
            all_errors.extend(structure_result.errors)
            all_warnings.extend(structure_result.warnings)
            
            # If structure is invalid, skip further validation
            if not structure_result.is_valid:
                return RuleValidationResult(False, all_errors, all_warnings)
        
        # Validate condition references
        if validate_condition:
            condition_result = self.validate_rule_condition(rule)
            all_errors.extend(condition_result.errors)
            all_warnings.extend(condition_result.warnings)
        
        # Validate syntax
        if validate_syntax:
            syntax_result = self.validate_rule_syntax(rule)
            all_errors.extend(syntax_result.errors)
            all_warnings.extend(syntax_result.warnings)
        
        return RuleValidationResult(len(all_errors) == 0, all_errors, all_warnings)
    
    def validate_rules_set(self, rules_set: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate an entire rules set.
        
        Args:
            rules_set: List of rule dictionaries to validate
            
        Returns:
            Dictionary containing:
                - is_valid: Whether all rules are valid
                - rules: List of per-rule validation results
                - summary: Summary statistics
        """
        results = []
        total_errors = 0
        total_warnings = 0
        
        for i, rule in enumerate(rules_set):
            rule_name = rule.get('rulename', rule.get('rule_name', f'Rule_{i}'))
            logger.debug("Validating rule", rule_name=rule_name, index=i)
            
            result = self.validate_rule(rule)
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
            
            results.append({
                'rule_name': rule_name,
                'index': i,
                'is_valid': result.is_valid,
                'errors': result.errors,
                'warnings': result.warnings
            })
        
        return {
            'is_valid': total_errors == 0,
            'rules': results,
            'summary': {
                'total_rules': len(rules_set),
                'valid_rules': sum(1 for r in results if r['is_valid']),
                'invalid_rules': sum(1 for r in results if not r['is_valid']),
                'total_errors': total_errors,
                'total_warnings': total_warnings
            }
        }


# Global validator instance
_validator: Optional[RuleValidator] = None


def get_rule_validator() -> RuleValidator:
    """
    Get global rule validator instance.
    
    Returns:
        RuleValidator instance
    """
    global _validator
    if _validator is None:
        _validator = RuleValidator()
    return _validator


def validate_rule(rule: Dict[str, Any]) -> RuleValidationResult:
    """
    Validate a single rule (convenience function).
    
    Args:
        rule: Rule dictionary to validate
        
    Returns:
        RuleValidationResult with validation status
        
    Example:
        >>> rule = {'rulename': 'TestRule', 'type': 'simple', ...}
        >>> result = validate_rule(rule)
        >>> if result:
        ...     print("Rule is valid")
    """
    validator = get_rule_validator()
    return validator.validate_rule(rule)


def validate_rules_set(rules_set: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a rules set (convenience function).
    
    Args:
        rules_set: List of rule dictionaries to validate
        
    Returns:
        Dictionary with validation results for all rules
        
    Example:
        >>> rules = [{'rulename': 'Rule1', ...}, {'rulename': 'Rule2', ...}]
        >>> results = validate_rules_set(rules)
        >>> print(f"Valid: {results['is_valid']}, Errors: {results['summary']['total_errors']}")
    """
    validator = get_rule_validator()
    return validator.validate_rules_set(rules_set)

