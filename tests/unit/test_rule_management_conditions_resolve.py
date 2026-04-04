"""
Unit tests for rule condition resolution (simple/complex) and DB rule_engine mapping.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.db_models import Base, Condition, RuleStatus
from common.exceptions import DataValidationError
from common.repository.db_repository import DatabaseConfigRepository
from services.rule_management import (
    _normalize_complex_mode,
    _resolve_rule_conditions_for_db,
)


@pytest.fixture
def resolve_session():
    """SQLite session with two conditions."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    session.add(
        Condition(
            condition_id="C1",
            name="n1",
            attribute="status",
            operator="equal",
            value="open",
            status=RuleStatus.ACTIVE.value,
        )
    )
    session.add(
        Condition(
            condition_id="C2",
            name="n2",
            attribute="priority",
            operator="greater_than",
            value="10",
            status=RuleStatus.ACTIVE.value,
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.unit
def test_normalize_complex_mode_aliases() -> None:
    assert _normalize_complex_mode("and") == "inclusive"
    assert _normalize_complex_mode("OR") == "exclusive"
    assert _normalize_complex_mode("inclusive") == "inclusive"


@pytest.mark.unit
def test_normalize_complex_mode_invalid() -> None:
    with pytest.raises(DataValidationError) as exc:
        _normalize_complex_mode("xor")
    assert exc.value.error_code == "RULE_INVALID_COMPLEX_MODE"


@pytest.mark.unit
def test_resolve_simple_by_item(resolve_session) -> None:
    attr, op, const, meta = _resolve_rule_conditions_for_db(
        resolve_session, {"item": "C1"}, "simple", {}
    )
    assert attr == "status"
    assert op == "equal"
    assert const == "open"
    assert meta["rule_engine"]["type"] == "simple"
    assert meta["rule_engine"]["conditions"] == {"item": "C1"}
    assert meta["condition_ids"]["condition_id"] == "C1"


@pytest.mark.unit
def test_resolve_complex_and(resolve_session) -> None:
    attr, op, const, meta = _resolve_rule_conditions_for_db(
        resolve_session,
        {"items": ["C1", "C2"], "mode": "and"},
        "complex",
        {},
    )
    assert attr == "status"
    assert meta["rule_engine"]["type"] == "complex"
    assert meta["rule_engine"]["conditions"]["items"] == ["C1", "C2"]
    assert meta["rule_engine"]["conditions"]["mode"] == "inclusive"
    assert "condition_ids" not in meta


@pytest.mark.unit
def test_resolve_missing_condition_raises(resolve_session) -> None:
    with pytest.raises(DataValidationError) as exc:
        _resolve_rule_conditions_for_db(resolve_session, {"item": "missing"}, "simple", {})
    assert exc.value.error_code == "CONDITION_NOT_FOUND"


@pytest.mark.unit
def test_database_config_repository_rule_to_dict_prefers_rule_engine() -> None:
    rule = SimpleNamespace(
        rule_id="R1",
        rule_name="Rule one",
        extra_metadata={
            "rule_engine": {
                "type": "complex",
                "conditions": {"items": ["C1", "C2"], "mode": "inclusive"},
            }
        },
        message="desc",
        rule_point=5,
        weight=1.0,
        priority=1,
        action_result="Y",
    )
    out = DatabaseConfigRepository()._rule_to_dict(rule)
    assert "attribute" not in out
    assert out["type"] == "complex"
    assert out["conditions"]["items"] == ["C1", "C2"]
    assert out["rulename"] == "Rule one"
