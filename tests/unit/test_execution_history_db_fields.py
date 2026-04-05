"""
Execution history persistence of ruleset_id and consumer_id.
"""

from unittest.mock import MagicMock, patch

import pytest

from common.execution_history import ExecutionHistory


@pytest.mark.unit
def test_log_execution_passes_ruleset_and_consumer_to_execution_log():
    history = ExecutionHistory(max_records=10, retention_days=1)
    mock_session = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_session
    mock_ctx.__exit__.return_value = None

    with patch("common.execution_history.get_db_session", return_value=mock_ctx):
        history.log_execution(
            input_data={"a": 1},
            output_data={"total_points": 1.0, "pattern_result": "Y"},
            execution_time_ms=12.0,
            correlation_id="corr-1",
            rules_evaluated=1,
            rules_matched=1,
            ruleset_id=99,
            consumer_id="client_a",
        )

    mock_session.add.assert_called_once()
    added = mock_session.add.call_args[0][0]
    assert added.ruleset_id == 99
    assert added.consumer_id == "client_a"
