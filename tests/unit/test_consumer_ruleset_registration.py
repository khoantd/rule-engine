"""
Unit tests for consumer ruleset registration service.
"""

import pytest
from unittest.mock import MagicMock, patch

from common.db_models import RuleStatus
from common.exceptions import DataValidationError, NotFoundError, SecurityError
from common.repository.config_repository import FileConfigRepository
from common.repository.db_repository import DatabaseConfigRepository
from services.consumer_ruleset_registration import ConsumerRulesetRegistrationService


class _StubDbRepo(DatabaseConfigRepository):
    """DatabaseConfigRepository stub that never hits the database."""

    def __init__(self, exact_id=None):
        self.default_ruleset_name = "default"
        self._exact_id = exact_id

    def get_active_ruleset_id_by_exact_name(self, ruleset_name):
        return self._exact_id


@pytest.fixture
def reg_repo():
    return MagicMock()


@pytest.fixture
def cons_repo():
    return MagicMock()


@pytest.fixture
def service(reg_repo, cons_repo):
    return ConsumerRulesetRegistrationService(
        registration_repository=reg_repo,
        consumer_repository=cons_repo,
    )


@pytest.mark.unit
def test_ensure_can_execute_skips_when_config_disabled(service):
    with patch("services.consumer_ruleset_registration.get_config") as m:
        m.return_value.require_consumer_ruleset_registration = False
        service.ensure_can_execute_ruleset(None, "any_ruleset")


@pytest.mark.unit
def test_ensure_can_execute_requires_consumer_id(service):
    with patch("services.consumer_ruleset_registration.get_config") as m:
        m.return_value.require_consumer_ruleset_registration = True
        with pytest.raises(DataValidationError) as exc:
            service.ensure_can_execute_ruleset(None, "rs")
        assert exc.value.error_code == "CONSUMER_ID_REQUIRED"


@pytest.mark.unit
def test_ensure_can_execute_requires_database_repository(service):
    with patch("services.consumer_ruleset_registration.get_config") as m:
        m.return_value.require_consumer_ruleset_registration = True
        with patch("services.consumer_ruleset_registration.get_config_repository") as gr:
            gr.return_value = FileConfigRepository()
            with pytest.raises(DataValidationError) as exc:
                service.ensure_can_execute_ruleset("c1", "rs")
            assert exc.value.error_code == "ENFORCEMENT_REQUIRES_DATABASE"


@pytest.mark.unit
def test_ensure_can_execute_security_when_not_registered(service, reg_repo, cons_repo):
    stub_db = _StubDbRepo(exact_id=5)
    cons_repo.get_consumer_by_consumer_id.return_value = MagicMock(status=RuleStatus.ACTIVE.value)
    reg_repo.get_active_registration.return_value = None
    with patch("services.consumer_ruleset_registration.get_config") as m:
        m.return_value.require_consumer_ruleset_registration = True
        with patch("services.consumer_ruleset_registration.get_config_repository") as gr:
            gr.return_value = stub_db
            with pytest.raises(SecurityError) as exc:
                service.ensure_can_execute_ruleset("c1", "myset")
            assert exc.value.error_code == "CONSUMER_RULESET_NOT_REGISTERED"


@pytest.mark.unit
def test_register_upserts(service, reg_repo, cons_repo):
    cons_repo.get_consumer_by_consumer_id.return_value = MagicMock(status=RuleStatus.ACTIVE.value)
    stub_db = _StubDbRepo(exact_id=3)
    row = MagicMock()
    row.to_dict = MagicMock(
        return_value={
            "id": 1,
            "consumer_id": "c1",
            "ruleset_id": 3,
            "status": "active",
            "created_at": None,
            "updated_at": None,
            "ruleset_name": "demo",
        }
    )
    reg_repo.upsert_active.return_value = row
    with patch("services.consumer_ruleset_registration.get_config_repository") as gr:
        gr.return_value = stub_db
        out = service.register("c1", "demo")
    reg_repo.upsert_active.assert_called_once_with("c1", 3)
    assert out["ruleset_name"] == "demo"


@pytest.mark.unit
def test_register_ruleset_not_found(service, cons_repo):
    cons_repo.get_consumer_by_consumer_id.return_value = MagicMock()
    stub_db = _StubDbRepo(exact_id=None)
    with patch("services.consumer_ruleset_registration.get_config_repository") as gr:
        gr.return_value = stub_db
        with pytest.raises(NotFoundError) as exc:
            service.register("c1", "missing")
        assert exc.value.error_code == "RULESET_NOT_FOUND"
