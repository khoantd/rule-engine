# Contributing to Rule Engine

Thank you for your interest in contributing to the Rule Engine project! This document provides guidelines and instructions for contributing code, documentation, and improvements.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please:

- Be respectful and considerate
- Welcome newcomers and help them learn
- Provide constructive feedback
- Focus on what is best for the project

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/rule-engine.git
   cd rule-engine
   ```
3. **Set up upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-org/rule-engine.git
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip and virtualenv
- Git

### Setup Steps

1. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   # or
   pip install -e ".[dev]"
   ```

3. **Verify setup**:
   ```bash
   pytest --version
   flake8 --version
   mypy --version
   black --version
   ```

### Pre-commit Hooks (Optional)

Set up pre-commit hooks to run checks automatically:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some project-specific conventions:

- **Line Length**: 100 characters (not 79)
- **Import Order**: Standard library, third-party, local imports
- **Type Hints**: Required for all public functions and methods
- **Docstrings**: Google-style docstrings for all public APIs

### Code Formatting

We use **Black** for code formatting:

```bash
# Format code
black .

# Check formatting
black --check .
```

**Configuration**: See `pyproject.toml` for Black settings.

### Import Organization

Use explicit imports, avoid wildcard imports:

```python
# Good ✅
from common.logger import get_logger
from common.exceptions import RuleEvaluationError, DataValidationError

# Bad ❌
from common.logger import *
from common.exceptions import *
```

### Type Hints

All public functions must have type hints:

```python
# Good ✅
def rules_exec(data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute rules against input data."""
    pass

# Bad ❌
def rules_exec(data):
    """Execute rules against input data."""
    pass
```

### Naming Conventions

- **Functions**: `snake_case` (e.g., `rules_exec`, `validate_input`)
- **Classes**: `PascalCase` (e.g., `RuleEvaluationError`, `ConfigLoader`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private**: Prefix with `_` (e.g., `_internal_helper`)

### Error Handling

Use custom exceptions from `common.exceptions`:

```python
# Good ✅
from common.exceptions import DataValidationError, RuleEvaluationError

if not data:
    raise DataValidationError("Input data cannot be None", error_code="DATA_NONE")

# Bad ❌
if not data:
    raise ValueError("Input data cannot be None")
```

### Logging

Use structured logging with context:

```python
# Good ✅
from common.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing rule", rule_id=rule_id, priority=priority)

# Bad ❌
print(f"Processing rule {rule_id}")
```

### Code Organization

- **One module per file**: Keep related functionality together
- **Separation of concerns**: Domain logic separate from infrastructure
- **DRY principle**: Don't repeat yourself, extract common functionality
- **Single Responsibility**: Each function/class should do one thing well

## Testing Requirements

### Test Structure

Tests are organized in `tests/` directory:

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
│   ├── test_ruleengine_exec.py
│   ├── test_workflow_exec.py
│   └── ...
├── integration/         # Integration tests
│   └── test_rule_execution.py
└── fixtures/            # Test data
```

### Writing Tests

**Unit Tests**:
- Test individual functions/methods in isolation
- Use mocks for external dependencies
- Fast execution (< 1 second per test)

**Integration Tests**:
- Test component interactions
- Use real configurations (but mocked external services)
- Can be slower but should still be reasonable

**Example**:

```python
import pytest
from services.ruleengine_exec import rules_exec
from common.exceptions import DataValidationError

class TestRulesExec:
    """Test suite for rules_exec function."""
    
    def test_rules_exec_with_valid_data(self):
        """Test rule execution with valid input data."""
        data = {'issue': 35, 'title': 'Superman'}
        result = rules_exec(data)
        
        assert 'total_points' in result
        assert 'pattern_result' in result
        assert 'action_recommendation' in result
    
    def test_rules_exec_with_invalid_data(self):
        """Test rule execution raises error with invalid data."""
        with pytest.raises(DataValidationError):
            rules_exec(None)
    
    def test_rules_exec_with_empty_data(self):
        """Test rule execution with empty data."""
        result = rules_exec({})
        assert result['total_points'] == 0.0
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
@pytest.mark.requires_config
def test_integration_function():
    pass
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Specific test file
pytest tests/unit/test_ruleengine_exec.py

# With coverage
pytest --cov=. --cov-report=html
```

### Coverage Requirements

- **Minimum Coverage**: 80% overall
- **New Code**: Should have 90%+ coverage
- **Critical Paths**: 100% coverage expected

Run coverage report:
```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
open htmlcov/index.html  # View HTML report
```

## Documentation Standards

### Docstrings

Use **Google-style** docstrings:

```python
def rules_exec(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute rules against input data.
    
    Args:
        data: Dictionary containing input data for rule evaluation
        
    Returns:
        Dictionary containing:
            - total_points: Sum of rule points
            - pattern_result: Concatenated action results
            - action_recommendation: Recommended action
            
    Raises:
        DataValidationError: If input data is invalid
        ConfigurationError: If configuration cannot be loaded
        RuleEvaluationError: If rule evaluation fails
        
    Example:
        >>> data = {'issue': 35, 'title': 'Superman'}
        >>> result = rules_exec(data)
        >>> result['total_points']
        1050.0
    """
    pass
```

### Module Docstrings

Every module should have a docstring:

```python
"""
Rule engine execution service.

This module provides the main entry point for rule execution,
including input validation, rule loading, and result processing.
"""
```

### README Updates

When adding features:
- Update README.md with examples
- Document configuration changes
- Add usage examples

### Code Comments

- Use comments to explain **why**, not **what**
- Complex logic should be commented
- Keep comments up-to-date with code changes

## Pull Request Process

### Before Submitting

1. **Update tests**: Add tests for new features or bug fixes
2. **Run tests**: Ensure all tests pass locally
3. **Run linters**: Fix any linting errors
4. **Update documentation**: Update README, docstrings, etc.
5. **Check coverage**: Ensure coverage doesn't decrease

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Type hints added for public functions
- [ ] No linting errors
- [ ] Coverage maintained or improved
- [ ] CHANGELOG updated (if applicable)

### PR Title Format

Use descriptive titles:
- `feat: Add support for custom rule operators`
- `fix: Resolve issue with empty pattern results`
- `docs: Update API documentation`
- `refactor: Simplify rule execution logic`
- `test: Add integration tests for workflow execution`

### PR Description

Include:
- **Purpose**: What problem does this solve?
- **Changes**: What was changed?
- **Testing**: How was it tested?
- **Screenshots/Examples**: If applicable

**Example**:

```markdown
## Purpose
Fixes issue where empty pattern results cause incorrect action recommendations.

## Changes
- Added validation for empty pattern strings
- Updated pattern matching logic to handle edge cases
- Added unit tests for empty pattern scenarios

## Testing
- Added test_empty_pattern_result() in test_ruleengine_exec.py
- All existing tests pass
- Manual testing with various pattern combinations

## Related Issues
Closes #123
```

### Review Process

1. **Automated Checks**: PR must pass CI/CD checks
2. **Code Review**: At least one maintainer approval required
3. **Address Feedback**: Respond to review comments
4. **Merge**: Squash and merge (preferred) or merge commit

### Branch Management

- **Feature branches**: `feature/description`
- **Bug fixes**: `fix/description`
- **Documentation**: `docs/description`
- **Refactoring**: `refactor/description`

## Issue Reporting

### Before Creating an Issue

1. Check existing issues for similar problems
2. Verify the issue exists in the latest version
3. Gather relevant information (logs, configurations, etc.)

### Issue Template

Use this template:

```markdown
**Description**
Clear description of the issue

**Steps to Reproduce**
1. Step one
2. Step two
3. ...

**Expected Behavior**
What should happen?

**Actual Behavior**
What actually happens?

**Environment**
- Python version:
- Package version:
- OS:

**Additional Context**
Logs, screenshots, configurations, etc.
```

### Bug Reports

Include:
- Minimal reproducible example
- Error messages/tracebacks
- Expected vs actual behavior
- Environment details

### Feature Requests

Include:
- Use case description
- Proposed solution
- Benefits
- Potential drawbacks

## Code Review Guidelines

### For Authors

- **Respond Promptly**: Address review comments quickly
- **Be Open**: Accept constructive feedback
- **Ask Questions**: If feedback is unclear
- **Update PR**: Make requested changes promptly

### For Reviewers

- **Be Constructive**: Provide actionable feedback
- **Be Respectful**: Focus on code, not person
- **Explain Why**: Justify requested changes
- **Approve When Ready**: Don't block unnecessarily

### Review Checklist

- Code follows style guidelines
- Tests are adequate
- Documentation is updated
- Performance considerations addressed
- Security concerns addressed
- Error handling is appropriate

## Release Process

Releases are handled by maintainers:

1. Update version in `__init__.py` and `pyproject.toml`
2. Update CHANGELOG
3. Create release tag
4. Build and publish package (if applicable)

## Getting Help

- **Documentation**: Check README and code comments
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions (if enabled)
- **Contact**: Reach out to maintainers

## Additional Resources

- [Code Quality Backlog](CODE_QUALITY_BACKLOG.md)
- [Architecture Documentation](ARCHITECTURE_IMPROVEMENTS.md)
- [Configuration Guide](CONFIGURATION_MANAGEMENT.md)
- [Testing Implementation](TESTING_IMPLEMENTATION.md)

---

Thank you for contributing to Rule Engine! 🎉

