"""Unit tests for execution query service."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from services.execution_query import ExecutionQueryService


@pytest.mark.unit
def test_list_executions_maps_rows_without_payload():
    row = MagicMock()
    row.id = 1
    row.execution_id = "e1"
    row.ruleset_id = 2
    row.consumer_id = "c1"
    row.total_points = 3.0
    row.pattern_result = "YY"
    row.execution_time_ms = 10.0
    row.success = True
    row.error_message = None
    row.timestamp = datetime(2026, 1, 1, 12, 0, 0)
    row.input_data = {"secret": "x"}
    row.output_data = {"y": 1}

    repo = MagicMock()
    repo.list_logs.return_value = ([row], 1)
    svc = ExecutionQueryService(repository=repo)
    out, total = svc.list_executions(consumer_id="c1", include_payload=False)
    assert total == 1
    assert out[0]["execution_id"] == "e1"
    assert out[0]["consumer_id"] == "c1"
    assert "input_data" not in out[0]


@pytest.mark.unit
def test_list_executions_include_payload():
    row = MagicMock()
    row.id = 1
    row.execution_id = "e1"
    row.ruleset_id = None
    row.consumer_id = None
    row.total_points = None
    row.pattern_result = None
    row.execution_time_ms = 1.0
    row.success = False
    row.error_message = "boom"
    row.timestamp = None
    row.input_data = {"a": 1}
    row.output_data = {"b": 2}

    repo = MagicMock()
    repo.list_logs.return_value = ([row], 1)
    svc = ExecutionQueryService(repository=repo)
    out, _ = svc.list_executions(include_payload=True)
    assert out[0]["input_data"] == {"a": 1}
    assert out[0]["output_data"] == {"b": 2}
