"""
Unit tests for hot reload validate-from-source (check invalid cases from DB).
"""

import pytest
from unittest.mock import MagicMock, patch

from services.hot_reload import HotReloadService


class TestValidateFromSource:
    """Tests for validate_from_source (rules/conditions from repository, e.g. DB)."""

    @patch("services.hot_reload.validate_rules_set")
    @patch("services.hot_reload.get_config_loader")
    def test_validate_from_source_returns_invalid_cases_with_rule_name_and_conditions(
        self, mock_get_loader, mock_validate_rules_set
    ):
        """Invalid rules from source include rule name and conditions in error message."""
        mock_loader = MagicMock()
        mock_repo = MagicMock()
        mock_repo.__class__.__name__ = "FileConfigRepository"
        mock_loader.repository = mock_repo
        mock_loader.load_rules_set.return_value = [
            {
                "rulename": "BadRule",
                "type": "simple",
                "priority": 1,
                "conditions": {"item": "MISSING_COND"},
                "rulepoint": 10.0,
                "weight": 1.0,
                "action_result": "A",
            }
        ]
        mock_get_loader.return_value = mock_loader

        mock_validate_rules_set.return_value = {
            "is_valid": False,
            "rules": [
                {
                    "rule_name": "BadRule",
                    "index": 0,
                    "is_valid": False,
                    "errors": [
                        {
                            "field": "conditions",
                            "error": "Rule 'BadRule' (conditions: condition_id='MISSING_COND'): condition 'MISSING_COND' not found in conditions set",
                            "severity": "error",
                            "configuration_error": "Rule 'BadRule' (conditions: condition_id='MISSING_COND'): condition 'MISSING_COND' not found in conditions set",
                        }
                    ],
                    "warnings": [],
                }
            ],
            "summary": {
                "total_rules": 1,
                "valid_rules": 0,
                "invalid_rules": 1,
                "total_errors": 1,
                "total_warnings": 0,
            },
        }

        service = HotReloadService()
        result = service.validate_from_source(source=None)

        assert result["is_valid"] is False
        assert result["summary"]["invalid_rules"] == 1
        assert len(result["rules"]) == 1
        assert result["rules"][0]["rule_name"] == "BadRule"
        assert not result["rules"][0]["is_valid"]
        err_msg = result["rules"][0]["errors"][0]["error"]
        assert "BadRule" in err_msg
        assert "MISSING_COND" in err_msg or "condition" in err_msg.lower()
        assert "source_type" in result

    @patch("services.hot_reload.validate_rules_set")
    @patch("services.hot_reload.get_config_loader")
    def test_validate_from_source_all_valid(self, mock_get_loader, mock_validate_rules_set):
        """When all rules are valid, result is_valid is True and invalid_rules is 0."""
        mock_loader = MagicMock()
        mock_repo = MagicMock()
        mock_repo.__class__.__name__ = "DatabaseConfigRepository"
        mock_loader.repository = mock_repo
        mock_repo.read_rules_set.return_value = [
            {"rulename": "R1", "type": "simple", "priority": 1, "conditions": {"item": "C1"}}
        ]
        mock_get_loader.return_value = mock_loader

        mock_validate_rules_set.return_value = {
            "is_valid": True,
            "rules": [
                {"rule_name": "R1", "index": 0, "is_valid": True, "errors": [], "warnings": []}
            ],
            "summary": {
                "total_rules": 1,
                "valid_rules": 1,
                "invalid_rules": 0,
                "total_errors": 0,
                "total_warnings": 0,
            },
        }

        service = HotReloadService()
        result = service.validate_from_source(source=None)

        assert result["is_valid"] is True
        assert result["summary"]["invalid_rules"] == 0
        assert result["source_type"] == "database"
        mock_repo.read_rules_set.assert_called_once_with(None)

    @patch("services.hot_reload.get_config_loader")
    def test_validate_from_source_empty_rules(self, mock_get_loader):
        """When source has no rules, returns is_valid True and empty rules list."""
        mock_loader = MagicMock()
        mock_repo = MagicMock()
        mock_repo.__class__.__name__ = "DatabaseConfigRepository"
        mock_loader.repository = mock_repo
        mock_repo.read_rules_set.return_value = []
        mock_get_loader.return_value = mock_loader

        service = HotReloadService()
        result = service.validate_from_source(source="my_ruleset")

        assert result["is_valid"] is True
        assert result["rules"] == []
        assert result["summary"]["total_rules"] == 0
        mock_repo.read_rules_set.assert_called_once_with("my_ruleset")
