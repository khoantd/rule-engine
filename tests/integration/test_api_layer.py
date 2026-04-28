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
def test_rules_execute_inline_subset_multiple_rules_dry_run(client: TestClient) -> None:
    # Force file-backed config for this test so it doesn't require a live DB.
    from common.repository.config_repository import FileConfigRepository, set_config_repository

    set_config_repository(FileConfigRepository())

    # The engine depends on the external `rule-engine` package's `rule_engine.Rule`.
    # In this repo, the local project directory name can shadow that import in some
    # environments, so we patch the minimal surface needed for deterministic tests.
    import common.rule_engine_util as reu

    class _DummyErrors:
        class SymbolResolutionError(Exception):
            pass

    class _DummyRule:
        def __init__(self, condition: str):
            self._condition = condition

        def matches(self, data):
            cond = (self._condition or "").strip()
            if "==" in cond:
                left, right = [p.strip() for p in cond.split("==", 1)]
                op = "=="
            elif ">" in cond:
                left, right = [p.strip() for p in cond.split(">", 1)]
                op = ">"
            else:
                raise ValueError(f"Unsupported condition: {cond}")

            if left not in data:
                raise _DummyErrors.SymbolResolutionError(f"Missing symbol '{left}'")

            lv = data[left]
            rv = right.strip()
            if (rv.startswith('"') and rv.endswith('"')) or (rv.startswith("'") and rv.endswith("'")):
                rv_val = rv[1:-1]
            else:
                try:
                    rv_val = float(rv)
                except ValueError:
                    rv_val = rv

            if op == "==":
                return str(lv) == str(rv_val)
            return float(lv) > float(rv_val)

    reu.rule_engine = type("_DummyRuleEngineModule", (), {"Rule": _DummyRule, "errors": _DummyErrors})()

    payload = {
        "data": {"amount": 150, "country": "US"},
        "dry_run": True,
        "rules": [
            {
                "id": "R-inline-1",
                "rule_name": "amount_gt_100",
                "type": "complex",
                "priority": 1,
                "conditions": {
                    "items": [{"attribute": "amount", "equation": "greater_than", "constant": "100"}],
                    "mode": "and",
                },
                "description": "amount > 100",
                "rule_point": 10.0,
                "weight": 1.0,
                "action_result": "Y",
            },
            {
                "id": "R-inline-2",
                "rule_name": "country_is_ca",
                "type": "complex",
                "priority": 2,
                "conditions": {
                    "items": [{"attribute": "country", "equation": "equal", "constant": "CA"}],
                    "mode": "and",
                },
                "description": "country == CA",
                "rule_point": 5.0,
                "weight": 1.0,
                "action_result": "N",
            },
        ],
    }

    response = client.post("/api/v1/rules/execute", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body.get("dry_run") is True
    assert isinstance(body.get("rule_evaluations"), list)
    assert len(body["rule_evaluations"]) == 2
    assert isinstance(body.get("would_match"), list)
    assert isinstance(body.get("would_not_match"), list)
    assert {r["rule_name"] for r in body["would_match"]} == {"amount_gt_100"}
    assert {r["rule_name"] for r in body["would_not_match"]} == {"country_is_ca"}


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


@pytest.mark.integration
def test_rules_execute_by_ids_fetches_then_executes_inline(client: TestClient) -> None:
    # Patch minimal rule_engine surface for deterministic tests (avoid importing external package).
    import common.rule_engine_util as reu

    class _DummyErrors:
        class SymbolResolutionError(Exception):
            pass

    class _DummyRule:
        def __init__(self, condition: str):
            self._condition = condition

        def matches(self, data):
            cond = (self._condition or "").strip()
            if "==" not in cond:
                raise ValueError(f"Unsupported condition: {cond}")
            left, right = [p.strip() for p in cond.split("==", 1)]
            if left not in data:
                raise _DummyErrors.SymbolResolutionError(f"Missing symbol '{left}'")
            rv = right.strip().strip('"').strip("'")
            return str(data[left]) == str(rv)

    reu.rule_engine = type("_DummyRuleEngineModule", (), {"Rule": _DummyRule, "errors": _DummyErrors})()

    # Avoid requiring a real conditions configuration file: we only use inline conditions dicts.
    reu.conditions_set_load = lambda: []

    class _FakeRuleService:
        def get_rule(self, rule_id: str):
            if rule_id == "R-1":
                return {
                    "id": "R-1",
                    "rulename": "r1",
                    "type": "complex",
                    "priority": 1,
                    "conditions": {
                        "items": [{"attribute": "zalo_id", "equation": "equal", "constant": "6819500480936506144"}],
                        "mode": "and",
                    },
                    "rulepoint": 10.0,
                    "weight": 1.0,
                    "action_result": "Y",
                }
            return None

    from api.deps import get_rule_management_service_dep

    app.dependency_overrides[get_rule_management_service_dep] = lambda: _FakeRuleService()
    try:
        payload = {
            "rule_ids": ["R-1"],
            "data": {"zalo_id": "6819500480936506144"},
            "dry_run": True,
            "correlation_id": "cid-1",
        }
        response = client.post("/api/v1/rules/execute-by-ids", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body.get("dry_run") is True
        assert body.get("total_points") == 10.0
        assert body.get("pattern_result") == "Y"
        assert isinstance(body.get("rule_evaluations"), list)
        assert len(body["rule_evaluations"]) == 1
    finally:
        app.dependency_overrides.pop(get_rule_management_service_dep, None)
