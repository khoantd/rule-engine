# Rule Engine Test Suite

This directory contains comprehensive tests for the Rule Engine codebase.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_ruleengine_exec.py
│   ├── test_workflow_exec.py
│   ├── test_rule_engine_util.py
│   └── test_json_util.py
├── integration/             # Integration tests
│   └── test_rule_execution.py
└── fixtures/                # Test data fixtures
    ├── rules_config.json
    └── conditions_config.json
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run unit tests only
```bash
pytest tests/unit/
```

### Run integration tests only
```bash
pytest tests/integration/
```

### Run specific test file
```bash
pytest tests/unit/test_ruleengine_exec.py
```

### Run specific test
```bash
pytest tests/unit/test_ruleengine_exec.py::TestRulesExec::test_rules_exec_success
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
```

### Run in parallel
```bash
pytest -n auto
```

### Run with markers
```bash
pytest -m unit              # Run only unit tests
pytest -m integration       # Run only integration tests
pytest -m "not slow"        # Skip slow tests
```

## Test Markers

- `unit`: Unit tests (fast, no external dependencies)
- `integration`: Integration tests (may use external dependencies)
- `slow`: Slow running tests
- `requires_config`: Tests that require configuration files
- `requires_aws`: Tests that require AWS credentials
- `requires_network`: Tests that require network access

## Coverage Goals

- **Target Coverage**: 80% (configured in `pytest.ini`)
- **Critical Modules**: Aim for 90%+ coverage
- **Coverage Reports**: 
  - Terminal: `--cov-report=term-missing`
  - HTML: `--cov-report=html` (generates `htmlcov/index.html`)
  - XML: `--cov-report=xml` (for CI/CD integration)

## Writing Tests

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_<function_name>_<scenario>`

### Example Test Structure

```python
import pytest
from unittest.mock import patch, MagicMock
from services.ruleengine_exec import rules_exec

class TestRulesExec:
    """Tests for rules_exec function."""
    
    @patch('services.ruleengine_exec.rules_set_setup')
    def test_rules_exec_success(self, mock_setup, sample_input_data):
        """Test successful rules execution."""
        # Arrange
        mock_setup.return_value = []
        
        # Act
        result = rules_exec(sample_input_data)
        
        # Assert
        assert "total_points" in result
```

### Using Fixtures

Common fixtures are available in `conftest.py`:

- `sample_input_data`: Sample input data for rule evaluation
- `sample_rules_config`: Sample rules configuration
- `sample_conditions_config`: Sample conditions configuration
- `mock_config_loader`: Mocked ConfigLoader
- `temp_config_file`: Temporary configuration file
- `mock_logger`: Mocked logger

### Mocking External Dependencies

```python
@patch('module.to.mock.function')
def test_with_mock(self, mock_function):
    mock_function.return_value = expected_value
    # Test code here
```

## Continuous Integration

Tests should be run in CI/CD pipelines with:

```bash
pytest --cov=. --cov-report=xml --cov-fail-under=80
```

## Test Data

Test data fixtures are located in `tests/fixtures/`:

- `rules_config.json`: Sample rules configuration
- `conditions_config.json`: Sample conditions configuration

## Best Practices

1. **One assertion per test** when possible (clarity)
2. **Use descriptive test names** that explain what is being tested
3. **Arrange-Act-Assert** pattern for test structure
4. **Mock external dependencies** to keep tests fast and isolated
5. **Use fixtures** for common test data and setup
6. **Test edge cases** and error conditions
7. **Keep tests independent** - no test should depend on another
8. **Write tests before or alongside code** (TDD/BDD approach)

## Troubleshooting

### Import Errors

If you encounter import errors, ensure the parent directory is in Python path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Cache Issues

Clear pytest cache:
```bash
pytest --cache-clear
```

### Coverage Not Accurate

Ensure coverage configuration in `pytest.ini` includes all relevant paths and excludes test directories.

