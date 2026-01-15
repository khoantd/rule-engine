"""
Unit tests for services.ruleengine_exec module.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import Dict, Any

from services.ruleengine_exec import validate_input_data, rules_exec
from common.exceptions import DataValidationError, RuleEvaluationError, ConfigurationError


class TestValidateInputData:
    """Tests for validate_input_data function."""
    
    def test_validate_input_data_valid_dict(self, sample_input_data):
        """Test validation with valid dictionary."""
        result = validate_input_data(sample_input_data)
        assert result == sample_input_data
    
    def test_validate_input_data_empty_dict(self):
        """Test validation with empty dictionary."""
        result = validate_input_data({})
        assert result == {}
    
    def test_validate_input_data_none(self):
        """Test validation with None raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_input_data(None)
        
        assert exc_info.value.error_code == "DATA_NONE"
    
    def test_validate_input_data_invalid_type(self):
        """Test validation with invalid type raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_input_data("not a dict")
        
        assert exc_info.value.error_code == "DATA_INVALID_TYPE"
    
    def test_validate_input_data_list(self):
        """Test validation with list raises DataValidationError."""
        with pytest.raises(DataValidationError) as exc_info:
            validate_input_data([1, 2, 3])
        
        assert exc_info.value.error_code == "DATA_INVALID_TYPE"


class TestRulesExec:
    """Tests for rules_exec function."""
    
    @patch('services.ruleengine_exec.rules_set_setup')
    @patch('services.ruleengine_exec.rules_set_cfg_read')
    @patch('services.ruleengine_exec.rule_run')
    @patch('services.ruleengine_exec.actions_set_cfg_read')
    @patch('services.ruleengine_exec.find_action_recommendation')
    def test_rules_exec_success(
        self,
        mock_find_action,
        mock_actions_cfg,
        mock_rule_run,
        mock_rules_cfg_read,
        mock_rules_set_setup,
        sample_input_data,
        sample_prepared_rules_list
    ):
        """Test successful rules execution."""
        # Setup mocks
        mock_rules_cfg_read.return_value = []
        mock_rules_set_setup.return_value = sample_prepared_rules_list
        mock_rule_run.side_effect = [
            {"action_result": "A", "rule_point": 10.0, "weight": 1.0},
            {"action_result": "B", "rule_point": 20.0, "weight": 1.5}
        ]
        mock_actions_cfg.return_value = {"AB": "APPROVED"}
        mock_find_action.return_value = "APPROVED"
        
        # Execute
        result = rules_exec(sample_input_data)
        
        # Assertions
        assert result["total_points"] == 40.0  # (10 * 1.0) + (20 * 1.5)
        assert result["pattern_result"] == "AB"
        assert result["action_recommendation"] == "APPROVED"
        mock_rules_set_setup.assert_called_once()
        assert mock_rule_run.call_count == 2
    
    def test_rules_exec_invalid_input(self):
        """Test rules_exec with invalid input raises DataValidationError."""
        with pytest.raises(DataValidationError):
            rules_exec(None)
    
    @patch('services.ruleengine_exec.rules_set_setup')
    @patch('services.ruleengine_exec.rules_set_cfg_read')
    def test_rules_exec_no_rules(
        self,
        mock_rules_cfg_read,
        mock_rules_set_setup,
        sample_input_data
    ):
        """Test rules_exec with no rules returns default result."""
        mock_rules_cfg_read.return_value = []
        mock_rules_set_setup.return_value = []
        
        result = rules_exec(sample_input_data)
        
        assert result["total_points"] == 0.0
        assert result["pattern_result"] == ""
        assert result["action_recommendation"] is None
    
    @patch('services.ruleengine_exec.rules_set_setup')
    @patch('services.ruleengine_exec.rules_set_cfg_read')
    def test_rules_exec_config_error(
        self,
        mock_rules_cfg_read,
        mock_rules_set_setup,
        sample_input_data
    ):
        """Test rules_exec with configuration error raises ConfigurationError."""
        mock_rules_cfg_read.return_value = []
        mock_rules_set_setup.side_effect = ConfigurationError("Config error", error_code="CONFIG_ERROR")
        
        with pytest.raises(ConfigurationError) as exc_info:
            rules_exec(sample_input_data)
        
        assert exc_info.value.error_code == "CONFIG_ERROR"
    
    @patch('services.ruleengine_exec.rules_set_setup')
    @patch('services.ruleengine_exec.rules_set_cfg_read')
    @patch('services.ruleengine_exec.rule_run')
    def test_rules_exec_invalid_rule_structure(
        self,
        mock_rule_run,
        mock_rules_cfg_read,
        mock_rules_set_setup,
        sample_input_data
    ):
        """Test rules_exec with invalid rule structure raises RuleEvaluationError."""
        mock_rules_cfg_read.return_value = []
        mock_rules_set_setup.return_value = ["not a dict"]  # Invalid rule
        
        with pytest.raises(RuleEvaluationError) as exc_info:
            rules_exec(sample_input_data)
        
        assert exc_info.value.error_code == "RULE_INVALID_STRUCTURE"
    
    @patch('services.ruleengine_exec.rules_set_setup')
    @patch('services.ruleengine_exec.rules_set_cfg_read')
    @patch('services.ruleengine_exec.rule_run')
    @patch('services.ruleengine_exec.actions_set_cfg_read')
    @patch('services.ruleengine_exec.find_action_recommendation')
    def test_rules_exec_rule_error_continues(
        self,
        mock_find_action,
        mock_actions_cfg,
        mock_rule_run,
        mock_rules_cfg_read,
        mock_rules_set_setup,
        sample_input_data,
        sample_prepared_rules_list
    ):
        """Test rules_exec continues execution when one rule fails."""
        mock_rules_cfg_read.return_value = []
        mock_rules_set_setup.return_value = sample_prepared_rules_list
        mock_rule_run.side_effect = [
            {"action_result": "A", "rule_point": 10.0, "weight": 1.0},
            Exception("Rule error")  # Second rule fails
        ]
        mock_actions_cfg.return_value = {"A": "APPROVED"}
        mock_find_action.return_value = "APPROVED"
        
        result = rules_exec(sample_input_data)
        
        # Should continue and return partial result
        assert result["total_points"] == 10.0
        assert result["pattern_result"] == "A"
    
    @patch('services.ruleengine_exec.rules_set_setup')
    @patch('services.ruleengine_exec.rules_set_cfg_read')
    @patch('services.ruleengine_exec.rule_run')
    @patch('services.ruleengine_exec.actions_set_cfg_read')
    @patch('services.ruleengine_exec.find_action_recommendation')
    def test_rules_exec_invalid_points_weight(
        self,
        mock_find_action,
        mock_actions_cfg,
        mock_rule_run,
        mock_rules_cfg_read,
        mock_rules_set_setup,
        sample_input_data,
        sample_prepared_rules_list
    ):
        """Test rules_exec handles invalid points/weight gracefully."""
        mock_rules_cfg_read.return_value = []
        mock_rules_set_setup.return_value = sample_prepared_rules_list
        mock_rule_run.return_value = {
            "action_result": "A",
            "rule_point": "invalid",  # Invalid type
            "weight": "invalid"  # Invalid type
        }
        mock_actions_cfg.return_value = {"A": "APPROVED"}
        mock_find_action.return_value = "APPROVED"
        
        result = rules_exec(sample_input_data)
        
        # Should handle gracefully with 0 points
        assert result["total_points"] == 0.0
        assert result["pattern_result"] == "AA"  # Both rules return "A"
    
    @patch('services.ruleengine_exec.rules_set_setup')
    @patch('services.ruleengine_exec.rules_set_cfg_read')
    @patch('services.ruleengine_exec.rule_run')
    @patch('services.ruleengine_exec.actions_set_cfg_read')
    def test_rules_exec_actions_config_error(
        self,
        mock_actions_cfg,
        mock_rule_run,
        mock_rules_cfg_read,
        mock_rules_set_setup,
        sample_input_data,
        sample_prepared_rules_list
    ):
        """Test rules_exec handles actions config error gracefully."""
        mock_rules_cfg_read.return_value = []
        mock_rules_set_setup.return_value = sample_prepared_rules_list
        mock_rule_run.return_value = {
            "action_result": "A",
            "rule_point": 10.0,
            "weight": 1.0
        }
        mock_actions_cfg.side_effect = ConfigurationError("Actions config error")
        
        result = rules_exec(sample_input_data)
        
        # Should continue without action recommendation
        assert result["action_recommendation"] is None

