"""
HTTP-level integration tests for the FastAPI application.

Uses dependency overrides to avoid database where possible.
"""

from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.deps import get_correlation_id, get_rule_management_service_dep
from api.main import app
from common.exceptions import NotFoundError

# Avoid BaseHTTPMiddleware/TaskGroup re-raising domain exceptions as ExceptionGroup in tests.
_client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client() -> TestClient:
    return _client


@pytest.mark.integration
def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "healthy"
    assert "X-Correlation-ID" in response.headers


@pytest.mark.integration
def test_rules_execute_validation_422(client: TestClient) -> None:
    response = client.post("/api/v1/rules/execute", json={})
    assert response.status_code == 422
    data = response.json()
    assert data.get("error_code") == "VALIDATION_ERROR"


@pytest.mark.integration
def test_not_found_error_shape_and_correlation_header(client: TestClient) -> None:
    class _FakeRuleService:
        def list_rules(self, ruleset_id: Optional[int] = None) -> List[Dict[str, Any]]:
            raise NotFoundError("gone", error_code="RULE_NOT_FOUND", context={"x": 1})

    app.dependency_overrides[get_rule_management_service_dep] = lambda: _FakeRuleService()
    try:
        response = client.get("/api/v1/management/rules")
        assert response.status_code == 404
        body = response.json()
        assert body.get("error_code") == "RULE_NOT_FOUND"
        assert "X-Correlation-ID" in response.headers
    finally:
        app.dependency_overrides.pop(get_rule_management_service_dep, None)


@pytest.mark.integration
def test_list_rules_with_stub_service(client: TestClient) -> None:
    class _EmptyRuleService:
        def list_rules(self, ruleset_id: Optional[int] = None) -> List[Dict[str, Any]]:
            return []

    app.dependency_overrides[get_rule_management_service_dep] = lambda: _EmptyRuleService()

    def _override_cid(request: Request) -> Optional[str]:
        return "test-cid-override"

    app.dependency_overrides[get_correlation_id] = _override_cid
    try:
        response = client.get("/api/v1/management/rules")
        assert response.status_code == 200
        body = response.json()
        assert body.get("count") == 0
        assert body.get("rules") == []
    finally:
        app.dependency_overrides.pop(get_rule_management_service_dep, None)
        app.dependency_overrides.pop(get_correlation_id, None)
