"""Tests for preventing duplicate rules (per ruleset) and create/update race handling."""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from common.db_models import Base, Rule, RuleStatus, Ruleset
from services.rule_management import RuleManagementService, _is_duplicate_ruleset_rule_id_error


def _memory_session_modules(monkeypatch: pytest.MonkeyPatch):
    """SQLite :memory: and patch get_db_session for rule_management + db_repository."""
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

    import common.repository.db_repository as db_repo_module
    import services.rule_management as rule_mgmt_module

    monkeypatch.setattr(rule_mgmt_module, "get_db_session", get_db_session_override)
    monkeypatch.setattr(db_repo_module, "get_db_session", get_db_session_override)
    return get_db_session_override


def _minimal_rule_kwargs(ruleset_id: int, rule_id: str, rule_name: str) -> dict:
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "attribute": "k",
        "condition": "equal",
        "constant": '"1"',
        "message": "m",
        "weight": 1.0,
        "rule_point": 1,
        "priority": 0,
        "action_result": "Y",
        "status": RuleStatus.ACTIVE.value,
        "version": "1.0",
        "ruleset_id": ruleset_id,
    }


@pytest.mark.unit
def test_is_duplicate_ruleset_rule_id_error_sqlite_message() -> None:
    """SQLite unique errors on rules table are recognized."""
    inner = Exception("UNIQUE constraint failed: rules.ruleset_id, rules.rule_id")
    exc = IntegrityError("stmt", {}, inner)
    assert _is_duplicate_ruleset_rule_id_error(exc) is True


@pytest.mark.unit
def test_is_duplicate_ruleset_rule_id_error_constraint_name() -> None:
    exc = IntegrityError("insert", {}, Exception("... uq_rules_ruleset_rule_id ..."))
    assert _is_duplicate_ruleset_rule_id_error(exc) is True


@pytest.mark.unit
def test_create_rule_unique_violation_falls_back_to_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    If insert races (stale read: get_rule empty) and DB rejects duplicate, update applies.
    """
    get_sess = _memory_session_modules(monkeypatch)
    ruleset_db_id = None
    with get_sess() as s:
        rs = Ruleset(
            name="rs_race",
            version="1.0",
            status=RuleStatus.ACTIVE.value,
            is_default=False,
        )
        s.add(rs)
        s.flush()
        ruleset_db_id = rs.id
        seed_kw = _minimal_rule_kwargs(rs.id, "R_RACE", "Old")
        seed_kw["message"] = "old desc"
        seed_kw["constant"] = '"1"'
        s.add(Rule(**seed_kw))

    service = RuleManagementService()
    monkeypatch.setattr(service, "get_rule", lambda _rid: None)

    out = service.create_rule(
        {
            "id": "R_RACE",
            "rule_name": "New",
            "description": "new desc",
            "result": "Z",
            "ruleset_id": ruleset_db_id,
            "conditions": {"attribute": "priority", "equation": "equal", "constant": '"9"'},
        }
    )
    assert out["id"] == "R_RACE"
    assert out["rule_name"] == "New"
    assert out["result"] == "Z"

    with get_sess() as s:
        row = s.query(Rule).filter(Rule.rule_id == "R_RACE").one()
        assert row.rule_name == "New"
        assert row.action_result == "Z"


@pytest.mark.unit
def test_database_unique_constraint_blocks_duplicate_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ORM metadata unique constraint blocks a second row with same (ruleset_id, rule_id)."""
    get_sess = _memory_session_modules(monkeypatch)
    with get_sess() as s:
        rs = Ruleset(
            name="rs_uq",
            version="1.0",
            status=RuleStatus.ACTIVE.value,
            is_default=False,
        )
        s.add(rs)
        s.flush()
        s.add(Rule(**_minimal_rule_kwargs(rs.id, "RX", "first")))

    with pytest.raises(IntegrityError):
        with get_sess() as s:
            rs_row = s.query(Ruleset).one()
            s.add(Rule(**_minimal_rule_kwargs(rs_row.id, "RX", "second")))
            # SQLite enforces unique on flush/commit
            s.flush()
