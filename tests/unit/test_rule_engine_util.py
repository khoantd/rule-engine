"""
Unit tests for common.rule_engine_util module.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import Dict, Any, List

from common.rule_engine_util import (
    rule_run,
    rule_prepare,
    rules_set_setup,
    rules_set_exec,
    find_action_recommendation,
    sort_by_priority,
    conditions_set_load
)
from common.exceptions import RuleEvaluationError, RuleCompilationError, ConfigurationError
from domain.conditions.condition_obj import Condition
from domain.rules.rule_obj import ExtRule


class TestRuleRun:
    """Tests for rule_run function."""
    
    @patch('common.rule_engine_util.rule_engine.Rule')
    def test_rule_run_success(self, mock_rule_class, sample_prepared_rule, sample_input_data):
        """Test successful rule execution."""
        mock_rule = MagicMock()
        mock_rule.matches.return_value = True
        mock_rule_class.return_value = mock_rule
        
        result = rule_run(sample_prepared_rule, sample_input_data)
        
        assert result["action_result"] == "A"
        assert result["rule_point"] == 10.0
        assert result["weight"] == 1.0
        mock_rule.matches.assert_called_once_with(sample_input_data)
    
    @patch('common.rule_engine_util.rule_engine.Rule')
    def test_rule_run_no_match(self, mock_rule_class, sample_prepared_rule, sample_input_data):
        """Test rule execution when rule doesn't match."""
        mock_rule = MagicMock()
        mock_rule.matches.return_value = False
        mock_rule_class.return_value = mock_rule
        
        result = rule_run(sample_prepared_rule, sample_input_data)
        
        assert result["action_result"] == "-"
        assert result["rule_point"] == 0.0
        assert result["weight"] == 0.0
    
    @patch('common.rule_engine_util.rule_engine.Rule')
    def test_rule_run_rule_error(self, mock_rule_class, sample_prepared_rule, sample_input_data):
        """Test rule execution handles rule engine errors gracefully."""
        import rule_engine.errors
        mock_rule_class.side_effect = rule_engine.errors.RuleError("Rule error")
        
        result = rule_run(sample_prepared_rule, sample_input_data)
        
        # Should return default values on error
        assert result["action_result"] == "-"
        assert result["rule_point"] == 0.0
    
    @patch('common.rule_engine_util.rule_engine.Rule')
    def test_rule_run_general_error(self, mock_rule_class, sample_prepared_rule, sample_input_data):
        """Test rule execution handles general errors gracefully."""
        mock_rule_class.side_effect = Exception("General error")
        
        result = rule_run(sample_prepared_rule, sample_input_data)
        
        # Should return default values on error
        assert result["action_result"] == "-"
        assert result["rule_point"] == 0.0


class TestRulePrepare:
    """Tests for rule_prepare function."""
    
    def test_rule_prepare_simple_rule(self, sample_condition_objects):
        """Test preparing a simple rule."""
        rule = {
            "rulename": "Rule1",
            "type": "simple",
            "priority": 1,
            "conditions": {"item": "C0001"},
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
        
        result = rule_prepare(sample_condition_objects, rule)
        
        assert result["rule_name"] == "Rule1"
        assert result["priority"] == 1
        assert "status" in result["condition"]  # Should contain attribute
        assert result["rule_point"] == 10.0
        assert result["action_result"] == "A"
        assert result["weight"] == 1.0
    
    def test_rule_prepare_complex_rule(self, sample_condition_objects):
        """Test preparing a complex rule."""
        rule = {
            "rulename": "Rule1",
            "type": "complex",
            "priority": 1,
            "conditions": {
                "items": ["C0001", "C0002"],
                "mode": "and"
            },
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
        
        result = rule_prepare(sample_condition_objects, rule)
        
        assert result["rule_name"] == "Rule1"
        assert result["priority"] == 1
        assert "and" in result["condition"].lower()  # Should contain logical operator
        assert result["rule_point"] == 10.0
    
    def test_rule_prepare_ext_rule(self, sample_condition_objects, sample_ext_rule):
        """Test preparing an ExtRule object."""
        result = rule_prepare(sample_condition_objects, sample_ext_rule)
        
        assert result["rule_name"] == "Rule1"
        assert result["priority"] == 1
    
    def test_rule_prepare_empty_rule(self, sample_condition_objects):
        """Test preparing empty rule raises RuleCompilationError."""
        with pytest.raises(RuleCompilationError) as exc_info:
            rule_prepare(sample_condition_objects, {})
        
        assert exc_info.value.error_code == "RULE_EMPTY"
    
    def test_rule_prepare_none_rule(self, sample_condition_objects):
        """Test preparing None rule raises RuleCompilationError."""
        with pytest.raises(RuleCompilationError) as exc_info:
            rule_prepare(sample_condition_objects, None)
        
        assert exc_info.value.error_code == "RULE_EMPTY"
    
    def test_rule_prepare_invalid_type(self, sample_condition_objects):
        """Test preparing rule with invalid type raises RuleCompilationError."""
        rule = {
            "rulename": "Rule1",
            "type": "invalid",
            "priority": 1,
            "conditions": {"item": "C0001"},
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
        
        with pytest.raises(RuleCompilationError) as exc_info:
            rule_prepare(sample_condition_objects, rule)
        
        assert exc_info.value.error_code == "RULE_INVALID_TYPE"
    
    def test_rule_prepare_simple_missing_item(self, sample_condition_objects):
        """Test preparing simple rule with missing item raises RuleCompilationError."""
        rule = {
            "rulename": "Rule1",
            "type": "simple",
            "priority": 1,
            "conditions": {},  # Missing item
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
        
        with pytest.raises(RuleCompilationError) as exc_info:
            rule_prepare(sample_condition_objects, rule)
        
        assert exc_info.value.error_code == "RULE_MISSING_CONDITION_ITEM"
    
    def test_rule_prepare_complex_missing_items(self, sample_condition_objects):
        """Test preparing complex rule with missing items raises RuleCompilationError."""
        rule = {
            "rulename": "Rule1",
            "type": "complex",
            "priority": 1,
            "conditions": {"mode": "and"},  # Missing items
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
        
        with pytest.raises(RuleCompilationError) as exc_info:
            rule_prepare(sample_condition_objects, rule)
        
        assert exc_info.value.error_code == "RULE_MISSING_CONDITIONS_ITEMS"
    
    def test_rule_prepare_complex_missing_mode(self, sample_condition_objects):
        """Test preparing complex rule with missing mode raises RuleCompilationError."""
        rule = {
            "rulename": "Rule1",
            "type": "complex",
            "priority": 1,
            "conditions": {"items": ["C0001"]},  # Missing mode
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
        
        with pytest.raises(RuleCompilationError) as exc_info:
            rule_prepare(sample_condition_objects, rule)
        
        assert exc_info.value.error_code == "RULE_MISSING_MODE"
    
    def test_rule_prepare_condition_not_found(self, sample_condition_objects):
        """Test preparing rule with condition not found raises ConfigurationError."""
        rule = {
            "rulename": "Rule1",
            "type": "simple",
            "priority": 1,
            "conditions": {"item": "NONEXISTENT"},
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
        
        with pytest.raises(ConfigurationError) as exc_info:
            rule_prepare(sample_condition_objects, rule)
        
        assert exc_info.value.error_code == "CONDITION_NOT_FOUND"
        msg = str(exc_info.value)
        assert "Rule1" in msg, "Error message should include rule name"
        assert "NONEXISTENT" in msg or "condition" in msg.lower(), (
            "Error message should include related condition (condition_id)"
        )

    def test_rule_prepare_flat_format_empty_attribute_raises_condition_empty(
        self, sample_condition_objects
    ):
        """Test flat-format rule with empty attribute raises RuleCompilationError CONDITION_EMPTY."""
        rule = {
            "rule_name": "Rule1",
            "attribute": "",
            "condition": "equal",
            "constant": "value",
            "message": "Empty attribute rule",
            "rule_point": 10.0,
            "weight": 1.0,
            "priority": 1,
            "action_result": "A",
        }
        with pytest.raises(RuleCompilationError) as exc_info:
            rule_prepare(sample_condition_objects, rule)
        assert exc_info.value.error_code == "CONDITION_EMPTY"
        msg = str(exc_info.value)
        assert "empty attribute" in msg.lower() or "cannot resolve" in msg.lower()
        assert "Rule1" in msg, "Error message should include rule name"
        assert "conditions:" in msg or "attribute=" in msg, (
            "Error message should include related conditions (attribute/condition/constant)"
        )


class TestFindActionRecommendation:
    """Tests for find_action_recommendation function."""
    
    def test_find_action_recommendation_success(self):
        """Test finding action recommendation successfully."""
        actions = {"AB": "APPROVED", "ABC": "REVIEWED"}
        result = find_action_recommendation(actions, "AB")
        assert result == "APPROVED"
    
    def test_find_action_recommendation_not_found(self):
        """Test finding action recommendation when not found returns None."""
        actions = {"AB": "APPROVED", "ABC": "REVIEWED"}
        result = find_action_recommendation(actions, "XYZ")
        assert result is None
    
    def test_find_action_recommendation_empty_actions(self):
        """Test finding action recommendation with empty actions returns None."""
        result = find_action_recommendation({}, "AB")
        assert result is None
    
    def test_find_action_recommendation_none_data(self):
        """Test finding action recommendation with None data returns None."""
        actions = {"AB": "APPROVED"}
        result = find_action_recommendation(actions, None)
        assert result is None
    
    def test_find_action_recommendation_invalid_type(self):
        """Test finding action recommendation with invalid type raises ValueError."""
        with pytest.raises(ValueError):
            find_action_recommendation("not a dict", "AB")


class TestSortByPriority:
    """Tests for sort_by_priority function."""
    
    def test_sort_by_priority(self):
        """Test sorting by priority."""
        rule1 = {"priority": 2, "name": "Rule2"}
        rule2 = {"priority": 1, "name": "Rule1"}
        
        rules = [rule1, rule2]
        sorted_rules = sorted(rules, key=sort_by_priority)
        
        assert sorted_rules[0]["priority"] == 1
        assert sorted_rules[1]["priority"] == 2


class TestRulesSetSetup:
    """Tests for rules_set_setup function."""
    
    @patch('common.rule_engine_util.conditions_set_load')
    @patch('common.rule_engine_util.get_file_cache')
    def test_rules_set_setup_success(
        self,
        mock_get_cache,
        mock_conditions_load,
        sample_condition_objects
    ):
        """Test successful rules setup."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Cache miss
        mock_get_cache.return_value = mock_cache
        mock_conditions_load.return_value = sample_condition_objects
        
        rules_set = [
            {
                "rulename": "Rule1",
                "type": "simple",
                "priority": 2,
                "conditions": {"item": "C0001"},
                "rulepoint": 10.0,
                "weight": 1.0,
                "action_result": "A"
            },
            {
                "rulename": "Rule2",
                "type": "simple",
                "priority": 1,
                "conditions": {"item": "C0002"},
                "rulepoint": 20.0,
                "weight": 1.5,
                "action_result": "B"
            }
        ]
        
        result = rules_set_setup(rules_set)
        
        # Should be sorted by priority
        assert len(result) == 2
        assert result[0]["priority"] == 1  # Lower priority first
        mock_cache.set.assert_called_once()
    
    @patch('common.rule_engine_util.get_file_cache')
    def test_rules_set_setup_cached(
        self,
        mock_get_cache
    ):
        """Test rules setup uses cache when available."""
        mock_cache = MagicMock()
        cached_result = [{"priority": 1, "rule_name": "Rule1"}]
        mock_cache.get.return_value = cached_result  # Cache hit
        mock_get_cache.return_value = mock_cache
        
        rules_set = []
        result = rules_set_setup(rules_set)
        
        assert result == cached_result
        mock_cache.set.assert_not_called()


class TestRulesSetExec:
    """Tests for rules_set_exec function."""
    
    def test_rules_set_exec_success(self, sample_condition_objects):
        """Test successful rules set execution."""
        rules_set = [
            {
                "rulename": "Rule1",
                "type": "simple",
                "priority": 1,
                "conditions": {"item": "C0001"},
                "rulepoint": 10.0,
                "weight": 1.0,
                "action_result": "A"
            }
        ]
        
        result = rules_set_exec(rules_set, sample_condition_objects)
        
        assert len(result) == 1
        assert result[0]["rule_name"] == "Rule1"

    def test_rules_set_exec_skips_empty_attribute_rule(self, sample_condition_objects):
        """Test that rules with empty attribute/condition are skipped with warning."""
        rules_set = [
            {
                "rulename": "Rule1",
                "type": "simple",
                "priority": 1,
                "conditions": {"item": "C0001"},
                "rulepoint": 10.0,
                "weight": 1.0,
                "action_result": "A",
            },
            {
                "rule_name": "Warm Lead",
                "attribute": "",
                "condition": "equal",
                "constant": "",
                "message": "Invalid rule",
            },
        ]
        result = rules_set_exec(rules_set, sample_condition_objects)
        # Only the valid rule should be in the result; "Warm Lead" is skipped
        assert len(result) == 1
        assert result[0]["rule_name"] == "Rule1"


class TestConditionsSetLoad:
    """Tests for conditions_set_load function."""
    
    @patch('common.rule_engine_util.conditions_set_cfg_read')
    def test_conditions_set_load_success(self, mock_cfg_read, sample_conditions_config):
        """Test successful conditions set load."""
        mock_cfg_read.return_value = sample_conditions_config
        
        result = conditions_set_load()
        
        assert len(result) == len(sample_conditions_config)
        assert all(isinstance(cond, Condition) for cond in result)

