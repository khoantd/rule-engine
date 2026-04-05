"""
FastAPI dependencies for request context and service access.

Use these with ``Depends()`` so tests can override factories via
``app.dependency_overrides``. Domain exceptions should propagate to the global
exception handler in ``api.middleware.errors`` rather than being caught in
every route.
"""

from typing import Optional

from fastapi import Request

from common.rule_registry import RuleRegistry, get_rule_registry
from services.ab_testing import ABTestingService, get_ab_testing_service
from services.actions_management import ActionsManagementService, get_actions_management_service
from services.attributes_management import (
    AttributesManagementService,
    get_attributes_management_service,
)
from services.conditions_management import (
    ConditionsManagementService,
    get_conditions_management_service,
)
from services.consumer_management import ConsumerManagementService, get_consumer_management_service
from services.consumer_ruleset_registration import (
    ConsumerRulesetRegistrationService,
    get_consumer_ruleset_registration_service,
)
from services.execution_query import ExecutionQueryService, get_execution_query_service
from services.hot_reload import HotReloadService, get_hot_reload_service
from services.rule_management import RuleManagementService, get_rule_management_service
from services.rule_versioning import RuleVersioningService, get_rule_versioning_service
from services.ruleset_management import RuleSetManagementService, get_ruleset_management_service
from services.workflow_management import WorkflowManagementService, get_workflow_management_service


def get_correlation_id(request: Request) -> Optional[str]:
    """Correlation ID from ``LoggingMiddleware`` (or None if missing)."""
    return getattr(request.state, "correlation_id", None)


def get_rule_registry_dep() -> RuleRegistry:
    """Rule registry singleton (override in tests)."""
    return get_rule_registry()


def get_hot_reload_service_dep() -> HotReloadService:
    """Hot reload service singleton (override in tests)."""
    return get_hot_reload_service()


def get_rule_management_service_dep() -> RuleManagementService:
    return get_rule_management_service()


def get_actions_management_service_dep() -> ActionsManagementService:
    return get_actions_management_service()


def get_conditions_management_service_dep() -> ConditionsManagementService:
    return get_conditions_management_service()


def get_attributes_management_service_dep() -> AttributesManagementService:
    return get_attributes_management_service()


def get_ruleset_management_service_dep() -> RuleSetManagementService:
    return get_ruleset_management_service()


def get_workflow_management_service_dep() -> WorkflowManagementService:
    return get_workflow_management_service()


def get_ab_testing_service_dep() -> ABTestingService:
    return get_ab_testing_service()


def get_rule_versioning_service_dep() -> RuleVersioningService:
    return get_rule_versioning_service()


def get_consumer_management_service_dep() -> ConsumerManagementService:
    return get_consumer_management_service()


def get_consumer_ruleset_registration_service_dep() -> ConsumerRulesetRegistrationService:
    return get_consumer_ruleset_registration_service()


def get_execution_query_service_dep() -> ExecutionQueryService:
    return get_execution_query_service()
