"""
Consumer registration to DB rulesets and enforcement helpers.
"""

from typing import Any, Dict, List, Optional

from common.config import get_config
from common.exceptions import DataValidationError, NotFoundError, SecurityError
from common.logger import get_logger
from common.repository.config_repository import get_config_repository
from common.repository.db_repository import (
    ConsumerRulesetRegistrationRepository,
    DatabaseConfigRepository,
    ConsumerRepository,
)
from common.db_models import RuleStatus

logger = get_logger(__name__)


class ConsumerRulesetRegistrationService:
    """Register consumers to rulesets and validate execute access."""

    def __init__(
        self,
        registration_repository: Optional[ConsumerRulesetRegistrationRepository] = None,
        consumer_repository: Optional[ConsumerRepository] = None,
    ) -> None:
        self._registration_repository = (
            registration_repository or ConsumerRulesetRegistrationRepository()
        )
        self._consumer_repository = consumer_repository or ConsumerRepository()

    def register(self, consumer_id: str, ruleset_name: str) -> Dict[str, Any]:
        """Create or reactivate a registration for an active ruleset."""
        cid = (consumer_id or "").strip()
        rname = (ruleset_name or "").strip()
        if not cid:
            raise DataValidationError(
                "consumer_id cannot be empty",
                error_code="CONSUMER_ID_EMPTY",
                context={},
            )
        if not rname:
            raise DataValidationError(
                "ruleset_name cannot be empty",
                error_code="RULESET_NAME_EMPTY",
                context={},
            )
        consumer = self._consumer_repository.get_consumer_by_consumer_id(cid)
        if not consumer:
            raise NotFoundError(
                "Consumer not found",
                error_code="CONSUMER_NOT_FOUND",
                context={"consumer_id": cid},
            )
        repo = get_config_repository()
        if not isinstance(repo, DatabaseConfigRepository):
            raise DataValidationError(
                "Ruleset registration requires database-backed configuration (USE_DATABASE)",
                error_code="REGISTRATION_REQUIRES_DATABASE",
                context={},
            )
        ruleset_db_id = repo.get_active_ruleset_id_by_exact_name(rname)
        if ruleset_db_id is None:
            raise NotFoundError(
                "Active ruleset not found",
                error_code="RULESET_NOT_FOUND",
                context={"ruleset_name": rname},
            )
        row = self._registration_repository.upsert_active(cid, ruleset_db_id)
        payload = row.to_dict(include_ruleset_name=False)
        payload["ruleset_name"] = rname
        return payload

    def list_registrations(
        self, consumer_id: str, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List registrations for a consumer."""
        cid = (consumer_id or "").strip()
        if not cid:
            raise DataValidationError(
                "consumer_id cannot be empty",
                error_code="CONSUMER_ID_EMPTY",
                context={},
            )
        consumer = self._consumer_repository.get_consumer_by_consumer_id(cid)
        if not consumer:
            raise NotFoundError(
                "Consumer not found",
                error_code="CONSUMER_NOT_FOUND",
                context={"consumer_id": cid},
            )
        rows = self._registration_repository.list_by_consumer(cid, active_only=active_only)
        return [r.to_dict(include_ruleset_name=True) for r in rows]

    def revoke(self, consumer_id: str, ruleset_name: str) -> None:
        """Revoke registration for a ruleset (by name)."""
        cid = (consumer_id or "").strip()
        rname = (ruleset_name or "").strip()
        if not cid:
            raise DataValidationError(
                "consumer_id cannot be empty",
                error_code="CONSUMER_ID_EMPTY",
                context={},
            )
        if not rname:
            raise DataValidationError(
                "ruleset_name cannot be empty",
                error_code="RULESET_NAME_EMPTY",
                context={},
            )
        consumer = self._consumer_repository.get_consumer_by_consumer_id(cid)
        if not consumer:
            raise NotFoundError(
                "Consumer not found",
                error_code="CONSUMER_NOT_FOUND",
                context={"consumer_id": cid},
            )
        repo = get_config_repository()
        if not isinstance(repo, DatabaseConfigRepository):
            raise DataValidationError(
                "Ruleset registration requires database-backed configuration (USE_DATABASE)",
                error_code="REGISTRATION_REQUIRES_DATABASE",
                context={},
            )
        ruleset_db_id = repo.get_active_ruleset_id_by_exact_name(rname)
        if ruleset_db_id is None:
            raise NotFoundError(
                "Active ruleset not found",
                error_code="RULESET_NOT_FOUND",
                context={"ruleset_name": rname},
            )
        ok = self._registration_repository.revoke(cid, ruleset_db_id)
        if not ok:
            raise NotFoundError(
                "Registration not found",
                error_code="CONSUMER_RULESET_REGISTRATION_NOT_FOUND",
                context={"consumer_id": cid, "ruleset_name": rname},
            )

    def ensure_can_execute_ruleset(self, consumer_id: Optional[str], ruleset_name: str) -> None:
        """
        When REQUIRE_CONSUMER_RULESET_REGISTRATION is enabled, validate consumer and registration.

        Raises:
            DataValidationError: Missing consumer_id or USE_DATABASE off
            NotFoundError: Unknown consumer or ruleset
            SecurityError: Inactive consumer or no active registration
        """
        cfg = get_config()
        if not cfg.require_consumer_ruleset_registration:
            return
        cid = (consumer_id or "").strip()
        if not cid:
            raise DataValidationError(
                "consumer_id is required when REQUIRE_CONSUMER_RULESET_REGISTRATION is enabled",
                error_code="CONSUMER_ID_REQUIRED",
                context={},
            )
        repo = get_config_repository()
        if not isinstance(repo, DatabaseConfigRepository):
            raise DataValidationError(
                "Consumer ruleset enforcement requires database-backed configuration (USE_DATABASE)",
                error_code="ENFORCEMENT_REQUIRES_DATABASE",
                context={},
            )
        consumer = self._consumer_repository.get_consumer_by_consumer_id(cid)
        if not consumer:
            raise NotFoundError(
                "Consumer not found",
                error_code="CONSUMER_NOT_FOUND",
                context={"consumer_id": cid},
            )
        if consumer.status != RuleStatus.ACTIVE.value:
            raise SecurityError(
                "Consumer is not active",
                error_code="CONSUMER_INACTIVE",
                context={"consumer_id": cid},
            )
        rname = (ruleset_name or "").strip()
        ruleset_db_id = repo.get_active_ruleset_id_by_exact_name(rname)
        if ruleset_db_id is None:
            raise NotFoundError(
                "Active ruleset not found",
                error_code="RULESET_NOT_FOUND",
                context={"ruleset_name": rname},
            )
        reg = self._registration_repository.get_active_registration(cid, ruleset_db_id)
        if not reg:
            raise SecurityError(
                "Consumer is not registered for this ruleset",
                error_code="CONSUMER_RULESET_NOT_REGISTERED",
                context={"consumer_id": cid, "ruleset_name": rname},
            )


_service: Optional[ConsumerRulesetRegistrationService] = None


def get_consumer_ruleset_registration_service() -> ConsumerRulesetRegistrationService:
    global _service
    if _service is None:
        _service = ConsumerRulesetRegistrationService()
    return _service


def set_consumer_ruleset_registration_service(
    service: Optional[ConsumerRulesetRegistrationService],
) -> None:
    global _service
    _service = service
