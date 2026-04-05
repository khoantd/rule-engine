"""Unit tests for filter_prepared_rules_by_input_data_keys."""

from unittest.mock import MagicMock, patch

import pytest

from common.rule_engine_util import filter_prepared_rules_by_input_data_keys


@pytest.mark.unit
class TestFilterPreparedRulesByInputDataKeys:
    """Tests for filter_prepared_rules_by_input_data_keys."""

    @patch("common.config.get_config")
    def test_disabled_returns_unchanged(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(filter_rules_by_input_keys=False)
        rules = [{"rule_name": "a", "referenced_attributes": ["x"]}]
        assert filter_prepared_rules_by_input_data_keys(rules, {"y": 1}) == rules

    @patch("common.config.get_config")
    def test_empty_data_dict_returns_unchanged(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(filter_rules_by_input_keys=True)
        rules = [{"rule_name": "a", "referenced_attributes": ["x"]}]
        assert filter_prepared_rules_by_input_data_keys(rules, {}) == rules

    @patch("common.config.get_config")
    def test_keeps_only_rules_whose_attrs_are_in_data(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(filter_rules_by_input_keys=True)
        rules = [
            {"rule_name": "phone_rule", "referenced_attributes": ["phone"]},
            {"rule_name": "email_rule", "referenced_attributes": ["email"]},
        ]
        out = filter_prepared_rules_by_input_data_keys(rules, {"phone": 1})
        assert len(out) == 1
        assert out[0]["rule_name"] == "phone_rule"

    @patch("common.config.get_config")
    def test_keeps_rules_without_referenced_attributes(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(filter_rules_by_input_keys=True)
        rules = [{"rule_name": "legacy"}]
        assert filter_prepared_rules_by_input_data_keys(rules, {"k": 1}) == rules

    @patch("common.config.get_config")
    def test_complex_rule_requires_all_attributes_in_data(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(filter_rules_by_input_keys=True)
        rules = [{"rule_name": "c", "referenced_attributes": ["a", "b"]}]
        assert filter_prepared_rules_by_input_data_keys(rules, {"a": 1}) == []
        assert len(filter_prepared_rules_by_input_data_keys(rules, {"a": 1, "b": 2})) == 1

    @patch("common.config.get_config")
    def test_non_dict_entries_pass_through(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(filter_rules_by_input_keys=True)
        rules = ["not-a-dict", {"rule_name": "ok", "referenced_attributes": ["x"]}]
        out = filter_prepared_rules_by_input_data_keys(rules, {"x": 1})
        assert out[0] == "not-a-dict"
        assert out[1]["rule_name"] == "ok"
