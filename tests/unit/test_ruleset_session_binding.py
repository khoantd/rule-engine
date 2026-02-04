"""
Unit tests for Ruleset session binding.

These tests ensure that creating a ruleset does not produce a detached ORM instance
that later triggers lazy-load errors (e.g., accessing Ruleset.patterns after the
original Session is closed).
"""

from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.db_models import Base
from services.ruleset_management import RuleSetManagementService


@pytest.mark.unit
def test_create_ruleset_does_not_open_nested_repository_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Validate the root-cause fix for detached Ruleset instances.

    RuleSetManagementService opens a DB session and calls RulesetRepository.create_ruleset().
    The repository must reuse the caller's Session (instead of opening a new one), otherwise
    the returned Ruleset can become detached and relationship lazy-loads will fail.
    """

    # Create an in-memory DB so ORM relationships/lazy-loads behave normally.
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

    # Patch the service module to use our in-memory DB session.
    import services.ruleset_management as ruleset_mgmt_module

    monkeypatch.setattr(ruleset_mgmt_module, "get_db_session", get_db_session_override)

    # If the repository tries to open its own session, fail the test (this is the root cause).
    import common.repository.db_repository as db_repo_module

    def repo_get_db_session_should_not_be_called():  # type: ignore[no-untyped-def]
        raise AssertionError(
            "RulesetRepository should reuse the caller's Session when provided; "
            "opening a nested session can detach the returned Ruleset and break lazy-loads."
        )

    monkeypatch.setattr(db_repo_module, "get_db_session", repo_get_db_session_should_not_be_called)

    service = RuleSetManagementService()

    # Avoid a DB query for existence check; focus this test on session behavior.
    monkeypatch.setattr(service, "get_ruleset", lambda _name: None)

    created = service.create_ruleset(
        {
            "ruleset_name": "rs_unit_test",
            "description": "unit test ruleset",
            "version": "1.0",
            "actionset": ["YYY", "Y--"],
            "rules": [],
        }
    )

    assert created["ruleset_name"] == "rs_unit_test"
    assert created["actionset"] == ["YYY", "Y--"]

