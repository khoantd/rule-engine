# Code Organization

This document describes the code organization structure of the Rule Engine codebase.

## Directory Structure

```
rule_engine/
├── __init__.py                  # Root package initialization
├── archive/                     # Deprecated/unused files (archived)
│   ├── README.md                # Archive documentation
│   ├── main_rule_exec_v1.py     # Deprecated v1 implementation
│   └── main_rule_exec_v2.py     # Deprecated v2 implementation
├── aws_main_rule_exec.py        # AWS Lambda entry point
├── main.py                      # Legacy main entry point
├── common/                      # Common utilities and helpers
│   ├── __init__.py              # Common package exports
│   ├── cache.py                 # Caching utilities
│   ├── config.py                # Configuration management
│   ├── config_loader.py         # Configuration loading
│   ├── conditions_enum.py       # Condition operators
│   ├── exceptions.py            # Custom exceptions
│   ├── json_util.py             # JSON utilities
│   ├── logger.py                # Logging utilities
│   ├── metrics.py               # Metrics collection
│   ├── rule_engine_util.py      # Rule engine utilities
│   ├── s3_aws_util.py           # S3/AWS utilities
│   ├── secrets_manager.py       # Secrets management
│   ├── security.py              # Security utilities
│   ├── util.py                  # General utilities
│   ├── di/                      # Dependency Injection
│   │   ├── __init__.py
│   │   ├── container.py
│   │   └── factory.py
│   ├── pattern/                 # Design patterns
│   │   ├── __init__.py
│   │   └── cor/                  # Chain of Responsibility
│   │       ├── __init__.py
│   │       └── handler.py
│   └── repository/               # Repository pattern
│       ├── __init__.py
│       ├── config_factory.py
│       └── config_repository.py
├── config/                      # Configuration files
│   └── config.ini
├── data/                        # Data files
│   └── input/                   # Input configuration files
│       ├── conditions_config.json
│       ├── rules_config.json
│       ├── rules_config_v2.json
│       ├── rules_config_v3.json
│       └── rules_config_v4.json
├── domain/                      # Domain models
│   ├── __init__.py
│   ├── jsonobj.py               # JSON serializable base class
│   ├── actions/                 # Action domain models
│   │   ├── __init__.py
│   │   └── action_obj.py
│   ├── conditions/              # Condition domain models
│   │   ├── __init__.py
│   │   └── condition_obj.py
│   ├── handler/                 # Workflow handlers
│   │   ├── __init__.py
│   │   ├── default_handler.py
│   │   ├── finishedcase_handler.py
│   │   ├── inprocesscase_handler.py
│   │   └── newcase_handler.py
│   ├── rules/                   # Rule domain models
│   │   ├── __init__.py
│   │   ├── rule_obj.py
│   │   └── ruleset_obj.py
│   └── ticket/                  # Ticket domain models
│       ├── __init__.py
│       ├── comic.py
│       └── ticket_obj.py
├── layers/                      # Lambda layers (external dependencies)
│   └── python/                  # Python dependencies
├── services/                    # Service layer
│   ├── __init__.py
│   ├── ruleengine_exec.py       # Rule execution service
│   └── workflow_exec.py         # Workflow execution service
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures
│   ├── fixtures/                # Test data
│   ├── integration/             # Integration tests
│   └── unit/                    # Unit tests
└── docs/                        # Documentation
```

## Package Organization

### Root Package (`__init__.py`)

The root package exports the main public API:

```python
from rule_engine import rules_exec, wf_exec
```

**Exports**:
- `rules_exec`: Main rule execution service
- `wf_exec`: Workflow execution service
- `__version__`: Package version
- `__author__`: Package author

### Common Package (`common/`)

Provides shared utilities and helper functions:

**Subpackages**:
- `common.di`: Dependency injection framework
- `common.pattern`: Design pattern implementations
- `common.repository`: Repository pattern for configuration

**Main Modules**:
- `common.exceptions`: Custom exception hierarchy
- `common.logger`: Structured logging
- `common.json_util`: JSON parsing and utilities
- `common.rule_engine_util`: Rule engine core utilities
- `common.config_loader`: Configuration loading with caching

### Domain Package (`domain/`)

Contains domain models and business logic:

**Subpackages**:
- `domain.actions`: Action domain objects
- `domain.conditions`: Condition domain objects
- `domain.rules`: Rule domain objects
- `domain.handler`: Workflow handlers (Chain of Responsibility)
- `domain.ticket`: Ticket domain objects

### Services Package (`services/`)

Provides high-level services:

**Modules**:
- `services.ruleengine_exec`: Rule execution service
- `services.workflow_exec`: Workflow execution service

## Public API Definition

Each `__init__.py` file uses `__all__` to explicitly define the public API:

### Benefits

1. **Explicit API**: Clear definition of what is public vs. private
2. **IDE Support**: Better autocomplete and IntelliSense
3. **Import Prevention**: Prevents accidental imports of private APIs
4. **Documentation**: Self-documenting package structure

### Example

```python
# services/__init__.py
from services.ruleengine_exec import rules_exec
from services.workflow_exec import wf_exec

__all__ = [
    'rules_exec',
    'wf_exec',
]
```

## Entry Points

### AWS Lambda

```python
from aws_main_rule_exec import lambda_handler

# Handler function for AWS Lambda
result = lambda_handler(event, context)
```

### Direct Execution

```python
from services.ruleengine_exec import rules_exec

# Execute rules directly
result = rules_exec(data)
```

### Workflow Execution

```python
from services.workflow_exec import wf_exec

# Execute workflow
result = wf_exec(process_name, stages, data)
```

## Deprecated Files

### Archive Directory

Deprecated files are moved to `archive/` directory:

- **`main_rule_exec_v1.py`**: Legacy v1 implementation (deprecated)
- **`main_rule_exec_v2.py`**: Legacy v2 implementation (deprecated)

**Migration Path**: Use `services.ruleengine_exec.rules_exec()` instead.

See `archive/README.md` for details on deprecated files and migration paths.

## File Naming Conventions

### Python Files

- **Modules**: `snake_case.py` (e.g., `rule_engine_util.py`)
- **Packages**: `snake_case/` (e.g., `rule_engine/`)
- **Classes**: `PascalCase` (e.g., `ConfigRepository`)
- **Functions**: `snake_case` (e.g., `rules_exec`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `S3_BUCKET_RULE_CONFIG`)

### Configuration Files

- **JSON**: `snake_case.json` (e.g., `rules_config.json`)
- **INI**: `config.ini`
- **Markdown**: `UPPER_SNAKE_CASE.md` (e.g., `CODE_ORGANIZATION.md`)

## Module Responsibilities

### Clear Separation of Concerns

1. **Domain Layer** (`domain/`): Business logic and domain models
2. **Service Layer** (`services/`): High-level business services
3. **Infrastructure Layer** (`common/`): Technical utilities and infrastructure
4. **Application Layer** (root): Application entry points

### Dependency Flow

```
Application Entry Points
    ↓
Services Layer
    ↓
Domain Layer
    ↓
Infrastructure/Common Layer
```

**Rule**: Higher layers can depend on lower layers, but not vice versa.

## Package Structure Best Practices

### 1. Explicit Imports

Use explicit imports instead of wildcard imports:

```python
# Good
from services.ruleengine_exec import rules_exec

# Bad
from services.ruleengine_exec import *
```

### 2. __all__ Definition

Every `__init__.py` should define `__all__`:

```python
__all__ = [
    'public_function',
    'PublicClass',
]
```

### 3. Package Documentation

Each package should have a docstring in `__init__.py`:

```python
"""
Package description.

This module provides:
- Feature 1
- Feature 2
"""
```

### 4. Consistent Structure

Follow consistent patterns across packages:
- `__init__.py` with `__all__`
- Documentation in package docstring
- Clear module separation

## Migration Guide

### From Legacy Files

If you're using deprecated files:

1. **From `main_rule_exec_v1.py` or `main_rule_exec_v2.py`**:
   ```python
   # Old
   from main_rule_exec_v1 import rules_exec
   
   # New
   from services.ruleengine_exec import rules_exec
   ```

2. **Update imports**:
   ```python
   # Old
   from common.json_util import *
   
   # New
   from common.json_util import read_json_file, parse_json_v2
   ```

3. **Use explicit imports**:
   ```python
   # Old
   from common import *
   
   # New
   from common import rules_exec, parse_json_v2
   ```

## Maintenance Guidelines

### Adding New Modules

1. Create module file with appropriate name
2. Add to appropriate package directory
3. Export in package `__init__.py` with `__all__`
4. Add documentation
5. Update this document if structure changes

### Removing Modules

1. Move to `archive/` directory if deprecated
2. Add entry to `archive/README.md`
3. Document migration path
4. Update imports in dependent code
5. Remove after grace period (if applicable)

### Refactoring

1. Maintain backward compatibility when possible
2. Document breaking changes
3. Provide migration guides
4. Update `__all__` definitions
5. Keep documentation up to date

## Standards Compliance

This codebase follows:

- **PEP 8**: Python style guide
- **PEP 257**: Docstring conventions
- **PEP 484**: Type hints (where applicable)
- **Python Package Guidelines**: Best practices for package structure

## Summary

The codebase is organized following Python best practices with:

✅ Clear package structure
✅ Explicit public APIs via `__all__`
✅ Consistent naming conventions
✅ Proper separation of concerns
✅ Deprecated file management
✅ Comprehensive documentation

For questions or improvements, refer to the project maintainers or open an issue.

