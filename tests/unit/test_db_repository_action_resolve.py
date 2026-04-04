"""
Unit tests for action recommendation resolution with linked Action rows.
"""

import pytest
from unittest.mock import MagicMock, patch

from common.db_models import Action, Pattern, RuleStatus
from common.repository.db_repository import (
    DatabaseConfigRepository,
    default_actionset_placeholder_message,
    format_action_recommendation_with_linked_actions,
    _linked_action_message_parts,
)


class TestLinkedActionMessageParts:
    """Tests for _linked_action_message_parts."""

    def test_empty_actions(self):
        assert _linked_action_message_parts(None) == []
        assert _linked_action_message_parts([]) == []

    def test_active_description_preferred(self):
        a = MagicMock()
        a.status = RuleStatus.ACTIVE.value
        a.id = 2
        a.description = "  Desc  "
        a.name = "N"
        b = MagicMock()
        b.status = RuleStatus.ACTIVE.value
        b.id = 1
        b.description = ""
        b.name = "Second"
        parts = _linked_action_message_parts([a, b])
        assert parts == ["Second", "Desc"]

    def test_skips_inactive(self):
        a = MagicMock()
        a.status = RuleStatus.INACTIVE.value
        a.id = 1
        a.description = "X"
        a.name = "Y"
        assert _linked_action_message_parts([a]) == []

    def test_configuration_message_fallback(self):
        a = MagicMock()
        a.status = RuleStatus.ACTIVE.value
        a.id = 1
        a.description = ""
        a.name = ""
        a.configuration = {"message": "  From JSON  "}
        assert _linked_action_message_parts([a]) == ["From JSON"]


class TestFormatActionRecommendationWithLinkedActions:
    """Tests for format_action_recommendation_with_linked_actions."""

    def test_no_linked_returns_base(self):
        assert format_action_recommendation_with_linked_actions("OK", None) == "OK"
        assert format_action_recommendation_with_linked_actions("OK", []) == "OK"

    def test_appends_linked_with_separator(self):
        a = MagicMock()
        a.status = RuleStatus.ACTIVE.value
        a.id = 1
        a.description = "Extra"
        a.name = "N"
        out = format_action_recommendation_with_linked_actions("Base", [a])
        assert out == "Base | Extra"

    def test_placeholder_replaced_by_linked_text_only(self):
        a = MagicMock()
        a.status = RuleStatus.ACTIVE.value
        a.id = 1
        a.description = "Real user message"
        a.name = "N"
        base = default_actionset_placeholder_message("YY")
        out = format_action_recommendation_with_linked_actions(base, [a], pattern_key="YY")
        assert out == "Real user message"


class TestResolveActionRecommendationForPattern:
    """Tests for DatabaseConfigRepository.resolve_action_recommendation_for_pattern."""

    def test_empty_pattern_returns_none(self):
        repo = DatabaseConfigRepository()
        assert repo.resolve_action_recommendation_for_pattern("rs", None) == (None, None)
        assert repo.resolve_action_recommendation_for_pattern("rs", "") == (None, None)
        assert repo.resolve_action_recommendation_for_pattern("rs", "   ") == (None, None)

    @patch("common.repository.db_repository.get_db_session")
    def test_no_ruleset_returns_none(self, mock_get_session):
        session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = session
        repo = DatabaseConfigRepository()
        repo._get_ruleset_by_name = MagicMock(return_value=None)
        repo._get_default_or_active_ruleset = MagicMock(return_value=None)

        assert repo.resolve_action_recommendation_for_pattern("missing", "AB") == (None, None)

    @patch("common.repository.db_repository.get_db_session")
    def test_match_without_linked_actions(self, mock_get_session):
        session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = session

        pattern = MagicMock()
        pattern.pattern_key = "YY"
        pattern.action_recommendation = "Approved"
        pattern.actions = []

        ruleset = MagicMock()
        ruleset.id = 1
        ruleset.name = "demo"

        repo = DatabaseConfigRepository()
        repo._get_ruleset_by_name = MagicMock(return_value=ruleset)

        def query_side_effect(model):
            q = MagicMock()
            if model is Pattern:
                q.options.return_value.filter.return_value.all.return_value = [pattern]
            elif model is Action:
                q.filter.return_value.all.return_value = []
            return q

        session.query.side_effect = query_side_effect

        display, base = repo.resolve_action_recommendation_for_pattern("demo", "YY")
        assert base == "Approved"
        assert display == "Approved"

    @patch("common.repository.db_repository.get_db_session")
    def test_match_with_linked_actions(self, mock_get_session):
        session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = session

        act = MagicMock()
        act.status = RuleStatus.ACTIVE.value
        act.id = 1
        act.description = "Notify user"
        act.name = "Notify"

        pattern = MagicMock()
        pattern.pattern_key = "YY"
        pattern.action_recommendation = "Approved"
        pattern.actions = [act]

        ruleset = MagicMock()
        ruleset.id = 1
        ruleset.name = "demo"

        repo = DatabaseConfigRepository()
        repo._get_ruleset_by_name = MagicMock(return_value=ruleset)

        def query_side_effect(model):
            q = MagicMock()
            if model is Pattern:
                q.options.return_value.filter.return_value.all.return_value = [pattern]
            elif model is Action:
                q.filter.return_value.all.return_value = []
            return q

        session.query.side_effect = query_side_effect

        display, base = repo.resolve_action_recommendation_for_pattern("demo", "YY")
        assert base == "Approved"
        assert display == "Approved | Notify user"

    @patch("common.repository.db_repository.get_db_session")
    def test_placeholder_replaced_when_linked_via_pattern(self, mock_get_session):
        session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = session

        act = MagicMock()
        act.status = RuleStatus.ACTIVE.value
        act.id = 1
        act.description = "Do the thing"
        act.name = "N"

        pattern = MagicMock()
        pattern.pattern_key = "YY"
        pattern.action_recommendation = default_actionset_placeholder_message("YY")
        pattern.actions = [act]

        ruleset = MagicMock()
        ruleset.id = 1
        ruleset.name = "demo"

        repo = DatabaseConfigRepository()
        repo._get_ruleset_by_name = MagicMock(return_value=ruleset)

        def query_side_effect(model):
            q = MagicMock()
            if model is Pattern:
                q.options.return_value.filter.return_value.all.return_value = [pattern]
            elif model is Action:
                q.filter.return_value.all.return_value = []
            return q

        session.query.side_effect = query_side_effect

        display, base = repo.resolve_action_recommendation_for_pattern("demo", "YY")
        assert base == default_actionset_placeholder_message("YY")
        assert display == "Do the thing"

    @patch("common.repository.db_repository.get_db_session")
    def test_orphan_action_matched_by_action_id_equals_pattern_key(self, mock_get_session):
        session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = session

        orphan = MagicMock()
        orphan.id = 5
        orphan.status = RuleStatus.ACTIVE.value
        orphan.description = "Orphan msg"
        orphan.name = "x"

        pattern = MagicMock()
        pattern.pattern_key = "YY"
        pattern.action_recommendation = default_actionset_placeholder_message("YY")
        pattern.actions = []

        ruleset = MagicMock()
        ruleset.id = 1
        ruleset.name = "demo"

        repo = DatabaseConfigRepository()
        repo._get_ruleset_by_name = MagicMock(return_value=ruleset)

        def query_side_effect(model):
            q = MagicMock()
            if model is Pattern:
                q.options.return_value.filter.return_value.all.return_value = [pattern]
            elif model is Action:
                q.filter.return_value.all.return_value = [orphan]
            return q

        session.query.side_effect = query_side_effect

        display, base = repo.resolve_action_recommendation_for_pattern("demo", "YY")
        assert display == "Orphan msg"
        assert base == default_actionset_placeholder_message("YY")

    @patch("common.repository.db_repository.get_db_session")
    def test_no_pattern_match_returns_none(self, mock_get_session):
        session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = session

        pattern = MagicMock()
        pattern.pattern_key = "XX"
        pattern.action_recommendation = "X"
        pattern.actions = []

        ruleset = MagicMock()
        ruleset.id = 1
        ruleset.name = "demo"

        repo = DatabaseConfigRepository()
        repo._get_ruleset_by_name = MagicMock(return_value=ruleset)

        def query_side_effect(model):
            q = MagicMock()
            if model is Pattern:
                q.options.return_value.filter.return_value.all.return_value = [pattern]
            elif model is Action:
                q.filter.return_value.all.return_value = []
            return q

        session.query.side_effect = query_side_effect

        assert repo.resolve_action_recommendation_for_pattern("demo", "ZZ") == (None, None)
