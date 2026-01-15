"""
Pytest configuration and shared fixtures.

This module contains fixtures that are available to all tests in the test suite.
"""

import json
import os
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch, PropertyMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.exceptions import ConfigurationError, RuleEvaluationError, DataValidationError
from common.config_loader import ConfigLoader
from common.repository.config_repository import ConfigRepository
from domain.conditions.condition_obj import Condition
from domain.rules.rule_obj import ExtRule


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_rules_config() -> Dict[str, Any]:
    """Return sample rules configuration."""
    return {
        "rules_set": [
            {
                "rulename": "Rule1",
                "type": "simple",
                "priority": 1,
                "conditions": {"item": "C0001"},
                "rulepoint": 10.0,
                "weight": 1.0,
                "action_result": "A"
            },
            {
                "rulename": "Rule2",
                "type": "simple",
                "priority": 2,
                "conditions": {"item": "C0002"},
                "rulepoint": 20.0,
                "weight": 1.5,
                "action_result": "B"
            },
            {
                "rulename": "Rule3",
                "type": "complex",
                "priority": 3,
                "conditions": {
                    "items": ["C0001", "C0002"],
                    "mode": "and"
                },
                "rulepoint": 30.0,
                "weight": 2.0,
                "action_result": "C"
            }
        ],
        "patterns": {
            "AB-": "APPROVED",
            "ABC": "REVIEWED",
            "-BC": "REJECTED"
        }
    }


@pytest.fixture
def sample_conditions_config() -> List[Dict[str, Any]]:
    """Return sample conditions configuration."""
    return [
        {
            "condition_id": "C0001",
            "condition_name": "Condition 1",
            "attribute": "status",
            "equation": "equal",
            "constant": "open"
        },
        {
            "condition_id": "C0002",
            "condition_name": "Condition 2",
            "attribute": "priority",
            "equation": "greater_than",
            "constant": "10"
        },
        {
            "condition_id": "C0003",
            "condition_name": "Condition 3",
            "attribute": "type",
            "equation": "range",
            "constant": ["bug", "feature"]
        }
    ]


@pytest.fixture
def sample_input_data() -> Dict[str, Any]:
    """Return sample input data for rule evaluation."""
    return {
        "status": "open",
        "priority": "15",
        "type": "bug",
        "issue": 35,
        "title": "Superman",
        "publisher": "DC"
    }


@pytest.fixture
def sample_prepared_rule() -> Dict[str, Any]:
    """Return a sample prepared rule ready for execution."""
    return {
        "priority": 1,
        "rule_name": "Rule1",
        "condition": "status == \"open\"",
        "rule_point": 10.0,
        "action_result": "A",
        "weight": 1.0
    }


@pytest.fixture
def sample_prepared_rules_list(sample_prepared_rule) -> List[Dict[str, Any]]:
    """Return a list of sample prepared rules."""
    return [
        sample_prepared_rule,
        {
            "priority": 2,
            "rule_name": "Rule2",
            "condition": "priority > \"10\"",
            "rule_point": 20.0,
            "action_result": "B",
            "weight": 1.5
        }
    ]


@pytest.fixture
def mock_config_repository() -> MagicMock:
    """Return a mocked ConfigRepository."""
    mock_repo = MagicMock(spec=ConfigRepository)
    return mock_repo


@pytest.fixture
def mock_config_loader(mock_config_repository) -> MagicMock:
    """Return a mocked ConfigLoader."""
    mock_loader = MagicMock(spec=ConfigLoader)
    mock_loader.load_rules_set.return_value = [
        {
            "rulename": "Rule1",
            "type": "simple",
            "priority": 1,
            "conditions": {"item": "C0001"},
            "rulepoint": 10.0,
            "weight": 1.0,
            "action_result": "A"
        }
    ]
    mock_loader.load_conditions_set.return_value = [
        {
            "condition_id": "C0001",
            "condition_name": "Condition 1",
            "attribute": "status",
            "equation": "equal",
            "constant": "open"
        }
    ]
    mock_loader.load_actions_set.return_value = {
        "AB": "APPROVED",
        "ABC": "REVIEWED"
    }
    return mock_loader


@pytest.fixture
def mock_rule_engine_rule() -> MagicMock:
    """Return a mocked rule_engine.Rule."""
    mock_rule = MagicMock()
    mock_rule.matches.return_value = True
    return mock_rule


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Return a mocked boto3 S3 client."""
    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b'{"test": "data"}'))
    }
    return mock_s3


@pytest.fixture
def temp_config_file(tmp_path) -> Path:
    """Create a temporary configuration file."""
    config_file = tmp_path / "test_config.json"
    config_data = {
        "rules_set": [],
        "patterns": {}
    }
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    return config_file


@pytest.fixture
def temp_rules_config_file(tmp_path, sample_rules_config) -> Path:
    """Create a temporary rules configuration file with sample data."""
    config_file = tmp_path / "rules_config.json"
    with open(config_file, 'w') as f:
        json.dump(sample_rules_config, f)
    return config_file


@pytest.fixture
def temp_conditions_config_file(tmp_path, sample_conditions_config) -> Path:
    """Create a temporary conditions configuration file with sample data."""
    config_file = tmp_path / "conditions_config.json"
    config_data = {"conditions_set": sample_conditions_config}
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    return config_file


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before each test."""
    from common.cache import get_file_cache
    cache = get_file_cache()
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def mock_logger():
    """Mock logger to avoid noise in test output."""
    with patch('common.logger.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_file_read():
    """Mock file reading operations."""
    with patch('builtins.open', create=True) as mock_open:
        yield mock_open


@pytest.fixture
def isolated_filesystem(tmp_path, monkeypatch):
    """Provide isolated filesystem for tests."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.fixture
def sample_condition_objects(sample_conditions_config) -> List[Condition]:
    """Return sample Condition objects."""
    return [Condition(**cond) for cond in sample_conditions_config]


@pytest.fixture
def sample_ext_rule() -> ExtRule:
    """Return a sample ExtRule object."""
    return ExtRule(
        rulename="Rule1",
        type="simple",
        priority=1,
        conditions={"item": "C0001"},
        rulepoint=10.0,
        weight=1.0,
        action_result="A"
    )


@pytest.fixture
def sample_lambda_event() -> Dict[str, Any]:
    """Return sample Lambda event."""
    return {
        "status": "open",
        "priority": "15",
        "type": "bug"
    }


@pytest.fixture
def sample_lambda_context() -> MagicMock:
    """Return sample Lambda context."""
    context = MagicMock()
    context.function_name = "test-function"
    context.function_version = "$LATEST"
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    context.memory_limit_in_mb = 128
    context.aws_request_id = "test-request-id"
    return context

