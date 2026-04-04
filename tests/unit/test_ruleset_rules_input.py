"""
Unit tests for RuleSet ``rules`` payload handling (id/rule_id coercion, strings, update).
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.db_models import Base
from common.exceptions import DataValidationError
from services.ruleset_management import RuleSetManagementService


def _install_memory_db_service(monkeypatch: pytest.MonkeyPatch) -> RuleSetManagementService:
    """RuleSetManagementService backed by SQLite :memory: with session patch."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    @contextmanager
    def get_db_session_override():  # type: ignore[no-untyped-def]
        session = SessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    import services.ruleset_management as ruleset_mgmt_module

    monkeypatch.setattr(ruleset_mgmt_module, "get_db_session", get_db_session_override)

    import common.repository.db_repository as db_repo_module

    def repo_get_db_session_should_not_be_called():  # type: ignore[no-untyped-def]
        raise AssertionError("Nested repository session must not be used in this test path.")

    monkeypatch.setattr(db_repo_module, "get_db_session", repo_get_db_session_should_not_be_called)

    service = RuleSetManagementService()
    monkeypatch.setattr(service, "get_ruleset", lambda _name: None)
    return service


@pytest.mark.unit
def test_create_ruleset_accepts_numeric_id_and_rule_id_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _install_memory_db_service(monkeypatch)
    created = service.create_ruleset(
        {
            "ruleset_name": "rs_rules_ids",
            "rules": [{"id": 35}, {"rule_id": "ext-ref"}],
        }
    )
    rule_ids = {r["rule_id"] for r in created["rules"]}
    assert rule_ids == {"35", "ext-ref"}


@pytest.mark.unit
def test_create_ruleset_accepts_string_rule_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _install_memory_db_service(monkeypatch)
    created = service.create_ruleset(
        {
            "ruleset_name": "rs_str_rules",
            "rules": ["R0001", " R0002 "],
        }
    )
    rule_ids = [r["rule_id"] for r in created["rules"]]
    assert rule_ids == ["R0001", "R0002"]


@pytest.mark.unit
def test_create_ruleset_rejects_dict_without_id_or_rule_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _install_memory_db_service(monkeypatch)
    with pytest.raises(DataValidationError) as exc:
        service.create_ruleset(
            {
                "ruleset_name": "rs_bad_rule",
                "rules": [{"rule_name": "only_name"}],
            }
        )
    assert exc.value.error_code == "RULE_RULE_ID_MISSING"


@pytest.mark.unit
def test_update_ruleset_replaces_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _install_memory_db_service(monkeypatch)
    service.create_ruleset(
        {
            "ruleset_name": "rs_replace",
            "rules": [{"id": "first"}, {"id": "second"}],
        }
    )
    updated = service.update_ruleset(
        "rs_replace",
        {"rules": [{"id": 99}, "only-str"]},
    )
    rule_ids = {r["rule_id"] for r in updated["rules"]}
    assert rule_ids == {"99", "only-str"}
    assert len(updated["rules"]) == 2


@pytest.mark.unit
def test_update_ruleset_empty_rules_clears(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _install_memory_db_service(monkeypatch)
    service.create_ruleset(
        {
            "ruleset_name": "rs_clear",
            "rules": [{"id": "x"}],
        }
    )
    updated = service.update_ruleset("rs_clear", {"rules": []})
    assert updated["rules"] == []


@pytest.mark.unit
def test_update_ruleset_replaces_actionset(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _install_memory_db_service(monkeypatch)
    service.create_ruleset(
        {
            "ruleset_name": "rs_act",
            "actionset": ["AAA", "BBB"],
        }
    )
    updated = service.update_ruleset("rs_act", {"actionset": ["YYY", "YNY"]})
    assert updated["actionset"] == ["YYY", "YNY"]


@pytest.mark.unit
def test_update_ruleset_empty_actionset_clears(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _install_memory_db_service(monkeypatch)
    service.create_ruleset(
        {
            "ruleset_name": "rs_act_clear",
            "actionset": ["ZZZ"],
        }
    )
    updated = service.update_ruleset("rs_act_clear", {"actionset": []})
    assert updated["actionset"] == []
