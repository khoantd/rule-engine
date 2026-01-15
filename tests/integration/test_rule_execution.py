"""
Integration tests for rule execution.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch

from services.ruleengine_exec import rules_exec
from common.exceptions import DataValidationError, RuleEvaluationError, ConfigurationError


@pytest.mark.integration
class TestRuleExecutionIntegration:
    """Integration tests for rule execution."""
    
    def test_end_to_end_rule_execution(
        self,
        temp_rules_config_file,
        temp_conditions_config_file,
        sample_input_data
    ):
        """Test end-to-end rule execution with real files."""
        # This test requires actual configuration files
        # In a real scenario, you would set up the config files properly
        
        # Mock the config reading to use our test files
        with patch('common.rule_engine_util.cfg_read') as mock_cfg_read:
            mock_cfg_read.side_effect = lambda section, key: {
                ("RULE", "file_name"): str(temp_rules_config_file),
                ("CONDITIONS", "file_name"): str(temp_conditions_config_file)
            }[(section, key)]
            
            with patch('common.repository.config_repository.read_json_file') as mock_read:
                # Setup mock to return our test data
                def read_file(file_path):
                    if "rules" in file_path:
                        return {
                            "rules_set": [
                                {
                                    "rulename": "Rule1",
                                    "type": "simple",
                                    "priority": 1,
                                    "conditions": {"item": "C0001"},
                                    "rulepoint": 10.0,
                                    "weight": 1.0,
                                    "action_result": "A"
                                }
                            ],
                            "patterns": {"A": "APPROVED"}
                        }
                    elif "conditions" in file_path:
                        return {
                            "conditions_set": [
                                {
                                    "condition_id": "C0001",
                                    "condition_name": "Condition 1",
                                    "attribute": "status",
                                    "equation": "equal",
                                    "constant": "open"
                                }
                            ]
                        }
                
                mock_read.side_effect = read_file
                
                # Execute
                result = rules_exec(sample_input_data)
                
                # Verify result structure
                assert "total_points" in result
                assert "pattern_result" in result
                assert "action_recommendation" in result
    
    def test_rule_execution_with_multiple_rules(self, sample_input_data):
        """Test rule execution with multiple rules."""
        # This would test with actual rule engine evaluation
        # For now, we'll test the structure
        with patch('services.ruleengine_exec.rules_set_setup') as mock_setup:
            mock_setup.return_value = [
                {
                    "priority": 1,
                    "rule_name": "Rule1",
                    "condition": "status == \"open\"",
                    "rule_point": 10.0,
                    "action_result": "A",
                    "weight": 1.0
                },
                {
                    "priority": 2,
                    "rule_name": "Rule2",
                    "condition": "priority > \"10\"",
                    "rule_point": 20.0,
                    "action_result": "B",
                    "weight": 1.5
                }
            ]
            
            with patch('services.ruleengine_exec.rule_run') as mock_run:
                mock_run.side_effect = [
                    {"action_result": "A", "rule_point": 10.0, "weight": 1.0},
                    {"action_result": "B", "rule_point": 20.0, "weight": 1.5}
                ]
                
                with patch('services.ruleengine_exec.actions_set_cfg_read') as mock_actions:
                    mock_actions.return_value = {"AB": "APPROVED"}
                    
                    with patch('services.ruleengine_exec.find_action_recommendation') as mock_find:
                        mock_find.return_value = "APPROVED"
                        
                        result = rules_exec(sample_input_data)
                        
                        # Verify calculations
                        assert result["total_points"] == 40.0  # (10 * 1.0) + (20 * 1.5)
                        assert result["pattern_result"] == "AB"
                        assert result["action_recommendation"] == "APPROVED"


@pytest.mark.integration
class TestWorkflowExecutionIntegration:
    """Integration tests for workflow execution."""
    
    @pytest.mark.skip(reason="Requires actual handler chain setup")
    def test_end_to_end_workflow_execution(self, sample_input_data):
        """Test end-to-end workflow execution."""
        from services.workflow_exec import wf_exec
        
        result = wf_exec("test_process", ["INITIATED", "NEW"], sample_input_data)
        
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Integration tests for performance."""
    
    def test_rule_execution_performance(self, sample_input_data):
        """Test rule execution performance with many rules."""
        import time
        
        with patch('services.ruleengine_exec.rules_set_setup') as mock_setup:
            # Create many rules
            many_rules = [
                {
                    "priority": i,
                    "rule_name": f"Rule{i}",
                    "condition": "status == \"open\"",
                    "rule_point": 10.0,
                    "action_result": "A",
                    "weight": 1.0
                }
                for i in range(100)
            ]
            mock_setup.return_value = many_rules
            
            with patch('services.ruleengine_exec.rule_run') as mock_run:
                mock_run.return_value = {
                    "action_result": "A",
                    "rule_point": 10.0,
                    "weight": 1.0
                }
                
                with patch('services.ruleengine_exec.actions_set_cfg_read'):
                    with patch('services.ruleengine_exec.find_action_recommendation'):
                        start_time = time.time()
                        result = rules_exec(sample_input_data)
                        end_time = time.time()
                        
                        execution_time = end_time - start_time
                        
                        # Should complete in reasonable time (adjust threshold as needed)
                        assert execution_time < 1.0  # 1 second for 100 rules
                        assert result["total_points"] == 1000.0  # 100 * 10.0

