"""Unit tests for database vs file rules source resolution in ConfigLoader."""

from unittest.mock import MagicMock, patch

import pytest

from common.config_loader import (
    _looks_like_file_based_rules_ref,
    _resolve_rules_source_for_repository,
)
from common.repository.config_repository import FileConfigRepository
from common.repository.db_repository import DatabaseConfigRepository


@pytest.mark.unit
class TestLooksLikeFileBasedRulesRef:
    """Tests for _looks_like_file_based_rules_ref."""

    def test_json_suffix(self) -> None:
        assert _looks_like_file_based_rules_ref("rules.json") is True

    def test_dmn_suffix(self) -> None:
        assert _looks_like_file_based_rules_ref("rules.DMN") is True

    def test_path_with_slash(self) -> None:
        assert _looks_like_file_based_rules_ref("data/input/x.json") is True

    def test_windows_path(self) -> None:
        assert _looks_like_file_based_rules_ref("data\\input\\x.json") is True

    def test_plain_ruleset_name(self) -> None:
        assert _looks_like_file_based_rules_ref("production_scoring") is False

    def test_empty(self) -> None:
        assert _looks_like_file_based_rules_ref("") is False


@pytest.mark.unit
class TestResolveRulesSourceForRepository:
    """Tests for _resolve_rules_source_for_repository."""

    def test_file_repository_passthrough(self) -> None:
        repo = FileConfigRepository()
        assert (
            _resolve_rules_source_for_repository(repo, "data/input/x.json") == "data/input/x.json"
        )

    @patch("common.config.get_config")
    def test_database_uses_explicit_default_ruleset_name(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(default_ruleset_name="my_ruleset")
        repo = DatabaseConfigRepository(default_ruleset_name="default")
        assert (
            _resolve_rules_source_for_repository(repo, "data/input/rules_config_v4.json")
            == "my_ruleset"
        )

    @patch("common.config.get_config")
    def test_database_path_like_ref_without_explicit_returns_none(
        self, mock_get_config: MagicMock
    ) -> None:
        mock_get_config.return_value = MagicMock(default_ruleset_name=None)
        repo = DatabaseConfigRepository()
        assert _resolve_rules_source_for_repository(repo, "data/input/rules_config_v4.json") is None

    @patch("common.config.get_config")
    def test_database_non_path_ref_used_as_ruleset_name(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = MagicMock(default_ruleset_name=None)
        repo = DatabaseConfigRepository()
        assert _resolve_rules_source_for_repository(repo, "staging_rules") == "staging_rules"
