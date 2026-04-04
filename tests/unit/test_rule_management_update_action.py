"""Unit tests for rule update result / action_result handling."""

from datetime import datetime

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from common.db_models import RuleStatus
from services.rule_management import RuleManagementService


def _fake_rule(action_result: str = "OLD") -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        rule_id="R1",
        rule_name="Rule",
        attribute="a",
        condition="equal",
        constant="1",
        message="desc",
        weight=1.0,
        rule_point=10,
        priority=0,
        action_result=action_result,
        status=RuleStatus.ACTIVE.value,
        version="1.0",
        ruleset_id=1,
        tags=None,
        extra_metadata=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        created_by=None,
        updated_by=None,
    )


@pytest.mark.unit
def test_api_merge_drops_stale_action_result_when_only_result_in_body() -> None:
    """Mirrors PUT /rules/{id} merge so result-only updates are not overwritten."""
    existing_rule = {
        "result": "OLD",
        "action_result": "OLD",
        "rule_name": "n",
    }
    update_data = {"result": "NEW"}
    rule_data = existing_rule.copy()
    rule_data.update(update_data)
    if "result" in update_data and "action_result" not in update_data:
        rule_data.pop("action_result", None)
    elif "action_result" in update_data and "result" not in update_data:
        rule_data.pop("result", None)
    assert rule_data["result"] == "NEW"
    assert "action_result" not in rule_data


@pytest.mark.unit
def test_api_merge_drops_stale_result_when_only_action_result_in_body() -> None:
    existing_rule = {
        "result": "OLD",
        "action_result": "OLD",
        "rule_name": "n",
    }
    update_data = {"action_result": "NEW"}
    rule_data = existing_rule.copy()
    rule_data.update(update_data)
    if "result" in update_data and "action_result" not in update_data:
        rule_data.pop("action_result", None)
    elif "action_result" in update_data and "result" not in update_data:
        rule_data.pop("result", None)
    assert rule_data["action_result"] == "NEW"
    assert "result" not in rule_data


@pytest.mark.unit
def test_update_rule_result_only_sets_action_result() -> None:
    """When only result is present, it maps to action_result."""
    captured: dict = {}
    fake = _fake_rule("OLD")

    repo = MagicMock()
    repo.get_rule_by_rule_id.return_value = fake

    def capture_update(rid: int, **kwargs):
        captured["kwargs"] = kwargs
        if "action_result" in kwargs:
            fake.action_result = kwargs["action_result"]
        return fake

    repo.update_rule.side_effect = capture_update

    svc = RuleManagementService(rule_repository=repo)
    out = svc.update_rule("R1", {"result": "NEW"})

    assert captured["kwargs"]["action_result"] == "NEW"
    assert out["result"] == "NEW"


@pytest.mark.unit
def test_update_rule_action_result_only_sets_action_result() -> None:
    """When only action_result is present, it is persisted."""
    captured: dict = {}
    fake = _fake_rule("OLD")

    repo = MagicMock()
    repo.get_rule_by_rule_id.return_value = fake

    def capture_update(rid: int, **kwargs):
        captured["kwargs"] = kwargs
        if "action_result" in kwargs:
            fake.action_result = kwargs["action_result"]
        return fake

    repo.update_rule.side_effect = capture_update

    svc = RuleManagementService(rule_repository=repo)
    out = svc.update_rule("R1", {"action_result": "ALT"})

    assert captured["kwargs"]["action_result"] == "ALT"
    assert out["action_result"] == "ALT"


@pytest.mark.unit
def test_update_rule_both_aliases_prefers_action_result() -> None:
    """If both keys are present, action_result wins (API may send both explicitly)."""
    captured: dict = {}
    fake = _fake_rule("OLD")

    repo = MagicMock()
    repo.get_rule_by_rule_id.return_value = fake

    def capture_update(rid: int, **kwargs):
        captured["kwargs"] = kwargs
        if "action_result" in kwargs:
            fake.action_result = kwargs["action_result"]
        return fake

    repo.update_rule.side_effect = capture_update

    svc = RuleManagementService(rule_repository=repo)
    out = svc.update_rule(
        "R1",
        {"result": "FROM_RESULT", "action_result": "FROM_ACTION"},
    )

    assert captured["kwargs"]["action_result"] == "FROM_ACTION"
    assert out["action_result"] == "FROM_ACTION"
