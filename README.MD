# Rule Engine

A flexible and extensible rule engine for evaluating business rules and workflows. This package provides a powerful framework for defining, executing, and managing complex business rules with support for weighted scoring, pattern matching, and workflow orchestration.

## Features

- **Rule Evaluation**: Execute business rules with priority-based ordering and weighted scoring
- **Pattern Matching**: Define action patterns for complex decision-making
- **Workflow Orchestration**: Chain workflow handlers using Chain of Responsibility pattern
- **Configuration Management**: Load rules from JSON files or AWS S3
- **AWS Lambda Support**: Ready-to-use Lambda handler for serverless deployments
- **Dependency Injection**: Flexible DI container for testability and extensibility
- **Structured Logging**: Comprehensive logging with correlation IDs
- **Type Safety**: Type hints throughout the codebase
- **Error Handling**: Custom exception hierarchy for better error management

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install from Requirements

```bash
# Clone the repository
git clone <repository-url>
cd rule_engine

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Development Installation

For development with all testing and linting tools:

```bash
pip install -r requirements-dev.txt
# Or use pyproject.toml with pip install -e ".[dev]"
```

## Quick Start

### Basic Rule Execution

```python
from services.ruleengine_exec import rules_exec

# Define input data
data = {
    'issue': 35,
    'title': 'Superman',
    'publisher': 'DC'
}

# Execute rules
result = rules_exec(data)

# Access results
print(f"Total Points: {result['total_points']}")
print(f"Pattern Result: {result['pattern_result']}")
print(f"Action Recommendation: {result['action_recommendation']}")
```

### Workflow Execution

```python
from services.workflow_exec import wf_exec

# Execute workflow
result = wf_exec(
    process_name='process_1',
    ls_stages=['NEW', 'INPROGESS', 'FINISHED'],
    data={'id': 1, 'name': 'John', 'dob': '01/01/1990'}
)

print(result)
```

### AWS Lambda Usage

```python
from aws_main_rule_exec import lambda_handler

# Lambda event
event = {
    'issue': 35,
    'title': 'Superman',
    'publisher': 'DC'
}

# Execute via Lambda handler
result = lambda_handler(event, context=None)
```

## Architecture

### System Overview

The Rule Engine follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    Entry Points                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   main.py    │  │ aws_main_... │  │ Direct API  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐             │
│  │ ruleengine_exec │  │  workflow_exec  │             │
│  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│  Domain Layer │ │ Common Utils │ │   Config     │
│               │ │              │ │  Repository  │
│ - Rules       │ │ - Logging    │ │              │
│ - Actions     │ │ - Exceptions│ │ - File       │
│ - Conditions  │ │ - JSON       │ │ - S3        │
│ - Handlers    │ │ - Cache      │ │              │
│ - Tickets     │ │ - Metrics    │ │              │
└───────────────┘ └──────────────┘ └──────────────┘
```

### Directory Structure

```
rule_engine/
├── __init__.py              # Root package exports
├── main.py                  # Legacy entry point
├── aws_main_rule_exec.py    # AWS Lambda handler
├── common/                  # Common utilities
│   ├── logger.py           # Structured logging
│   ├── exceptions.py        # Custom exceptions
│   ├── json_util.py        # JSON utilities
│   ├── rule_engine_util.py # Core rule utilities
│   ├── config_loader.py    # Configuration loading
│   ├── di/                 # Dependency injection
│   ├── pattern/            # Design patterns (CoR)
│   └── repository/         # Configuration repository
├── domain/                 # Domain models
│   ├── rules/             # Rule domain objects
│   ├── actions/           # Action domain objects
│   ├── conditions/        # Condition domain objects
│   ├── handler/           # Workflow handlers
│   └── ticket/            # Ticket domain objects
├── services/              # Service layer
│   ├── ruleengine_exec.py # Rule execution service
│   └── workflow_exec.py   # Workflow execution service
├── config/                # Configuration files
├── data/                  # Data files
│   └── input/            # Rule configuration JSON
├── tests/                # Test suite
└── docs/                 # Documentation
```

### Key Components

#### 1. Service Layer (`services/`)

**Rule Engine Service** (`ruleengine_exec.py`):
- Main entry point for rule execution
- Validates input data
- Loads and executes rules
- Calculates weighted scores
- Performs pattern matching

**Workflow Service** (`workflow_exec.py`):
- Executes multi-stage workflows
- Chains handlers using CoR pattern
- Validates workflow inputs
- Manages workflow state

#### 2. Domain Layer (`domain/`)

**Rules** (`domain/rules/`):
- Rule objects and rule sets
- Rule configuration models

**Handlers** (`domain/handler/`):
- Chain of Responsibility pattern
- Stage-specific handlers (NEW, INPROGESS, FINISHED)
- Default handler fallback

**Conditions & Actions**:
- Condition evaluation logic
- Action result processing

#### 3. Common Utilities (`common/`)

**Configuration Management**:
- `config_loader.py`: Cached configuration loading
- `config.py`: Centralized configuration
- `repository/`: Repository pattern for config sources

**Logging & Error Handling**:
- `logger.py`: Structured logging with correlation IDs
- `exceptions.py`: Custom exception hierarchy

**Infrastructure**:
- `di/`: Dependency injection container
- `pattern/cor/`: Chain of Responsibility implementation
- `cache.py`: Caching utilities

## Configuration

### Rule Configuration

Rules can be defined in two formats:
1. **JSON format** (default): `data/input/rules_config.json` (or `rules_config_v4.json`)
2. **DMN format**: `data/input/sample_rules.dmn` (Decision Model Notation XML files)

The rule engine automatically detects the file format and parses it accordingly.

**Configuration Structure**:

```json
{
  "rules_set": [
    {
      "id": "R0001",
      "rule_name": "Rule 1",
      "attribute": "issue",
      "condition": "greater_than",
      "constant": "30",
      "message": "the issue is greater than 30",
      "weight": 30,
      "rule_point": 20,
      "priority": 1,
      "action_result": "Y"
    }
  ],
  "patterns": {
    "YYY": "Approved",
    "Y--": "Rejected",
    "YY-": "Reviewed"
  }
}
```

**Rule Fields**:
- `id`: Unique rule identifier
- `rule_name`: Human-readable rule name
- `attribute`: Data attribute to evaluate
- `condition`: Condition operator (see supported operators below)
- `constant`: Constant value for comparison
- `weight`: Weight multiplier for scoring
- `rule_point`: Base points awarded when rule matches
- `priority`: Execution priority (lower = higher priority)
- `action_result`: Result character (e.g., "Y", "N", "-")

**Pattern Fields**:
- Keys: Pattern strings (e.g., "YYY", "Y--")
- Values: Action recommendations (e.g., "Approved", "Rejected")

### Condition Operators

Supported condition operators (defined in `common/conditions_enum.py`):

- `equal`: Equality check (`==`)
- `not_equal`: Inequality check (`!=`)
- `greater_than`: Greater than (`>`)
- `greater_than_or_equal`: Greater than or equal (`>=`)
- `less_than`: Less than (`<`)
- `less_than_or_equal`: Less than or equal (`<=`)
- `in`: Membership check (`in`)
- `not_in`: Non-membership check (`not in`)
- `range`: Range check (`in [list]`)
- `contains`: String contains
- `regex`: Regular expression match

### DMN File Support

The rule engine supports parsing DMN (Decision Model Notation) XML files. DMN files contain decision tables that are automatically converted to the internal rule format.

**Example DMN Usage**:

```python
from common.dmn_parser import DMNParser

parser = DMNParser()
result = parser.parse_file('data/input/sample_rules.dmn')
rules = result['rules_set']
```

**Supported FEEL Expressions**:
- Comparison: `>`, `>=`, `<`, `<=`
- Equality: `"value"`, `'value'`
- Ranges: `[5..10]`
- Empty: `-` (matches anything)

See `DMN_PARSER_FEATURE.md` for detailed documentation on DMN support.

### Environment Configuration

Configuration can be overridden via environment variables:

```bash
# Configuration file paths
export RULES_CONFIG_PATH=data/input/rules_config_v4.json
export CONDITIONS_CONFIG_PATH=data/input/conditions_config.json

# AWS Configuration
export AWS_REGION=us-east-1
export S3_BUCKET=my-config-bucket
export S3_CONFIG_PREFIX=config/

# Environment
export ENVIRONMENT=production
```

### Configuration Sources

The engine supports multiple configuration sources:

1. **Local Files**: Default configuration from `data/input/`
2. **AWS S3**: Load configurations from S3 buckets
3. **Environment Variables**: Override specific settings

To use S3:

```python
from common.s3_aws_util import aws_s3_config_file_read

# Read from S3
config = aws_s3_config_file_read(
    bucket='my-config-bucket',
    key='config/rules_config.json'
)
```

## Usage Examples

### Example 1: Simple Rule Evaluation

```python
from services.ruleengine_exec import rules_exec

# Sample input data
data = {
    'issue': 35,        # Issue number > 30
    'title': 'Superman', # Title equals 'Superman'
    'publisher': 'DC'   # Publisher in ['DC', 'Marvel']
}

# Execute rules
result = rules_exec(data)

# Result structure:
# {
#     'total_points': 1050.0,  # (20 * 30) + (15 * 20) + (10 * 5)
#     'pattern_result': 'YYY', # All three rules matched
#     'action_recommendation': 'Approved'
# }
```

### Example 2: Workflow Execution

```python
from services.workflow_exec import wf_exec

# Execute multi-stage workflow
result = wf_exec(
    process_name='ticket_processing',
    ls_stages=['NEW', 'INPROGESS', 'FINISHED'],
    data={
        'ticket_id': 'TICK-123',
        'title': 'Issue Report',
        'priority': 'high'
    }
)

# Each stage processes the data through its handler
# The result contains the final processed data
```

### Example 3: Custom Rule Evaluation

```python
from common.rule_engine_util import rule_run
from domain.rules.rule_obj import ExtRule

# Define a rule manually
rule = {
    'rule_name': 'custom_rule',
    'priority': 1,
    'condition': 'issue greater_than 30',
    'rule_point': 20,
    'weight': 1.5,
    'action_result': 'Y'
}

# Execute single rule
data = {'issue': 35}
result = rule_run(rule, data)

print(result['rule_point'])  # 20
print(result['action_result'])  # 'Y'
```

### Example 4: AWS Lambda Deployment

```python
# lambda_handler.py
from aws_main_rule_exec import lambda_handler

def handler(event, context):
    """
    AWS Lambda handler.
    
    Expected event structure:
    {
        'issue': 35,
        'title': 'Superman',
        'publisher': 'DC'
    }
    """
    return lambda_handler(event, context)
```

**Lambda Event**:
```json
{
  "issue": 35,
  "title": "Superman",
  "publisher": "DC"
}
```

**Lambda Response**:
```json
{
  "total_points": 1050.0,
  "pattern_result": "YYY",
  "action_recommendation": "Approved"
}
```

## API Reference

### Main Entry Points

#### `rules_exec(data: Dict[str, Any]) -> Dict[str, Any]`

Execute rules against input data.

**Parameters**:
- `data`: Dictionary containing input data for rule evaluation

**Returns**:
- `total_points`: Sum of weighted rule points
- `pattern_result`: Concatenated action results (e.g., "YYY")
- `action_recommendation`: Recommended action based on pattern

**Raises**:
- `DataValidationError`: If input data is invalid
- `ConfigurationError`: If configuration cannot be loaded
- `RuleEvaluationError`: If rule evaluation fails

**Example**:
```python
from services.ruleengine_exec import rules_exec

result = rules_exec({'issue': 35, 'title': 'Superman'})
```

#### `wf_exec(process_name: str, ls_stages: List[str], data: Dict[str, Any]) -> Optional[Dict[str, Any]]`

Execute workflow with given process name, stages, and data.

**Parameters**:
- `process_name`: Name of the process/workflow
- `ls_stages`: List of workflow stage names
- `data`: Input data dictionary

**Returns**:
- Final workflow result dictionary, or None if execution fails

**Raises**:
- `DataValidationError`: If input data is invalid
- `WorkflowError`: If workflow execution fails

**Example**:
```python
from services.workflow_exec import wf_exec

result = wf_exec('process_1', ['NEW', 'INPROGESS', 'FINISHED'], {'id': 1})
```

#### `lambda_handler(event: Any, context: Any) -> Dict[str, Any]`

AWS Lambda handler for rule engine execution.

**Parameters**:
- `event`: Lambda event (must be a dictionary)
- `context`: Lambda context object

**Returns**:
- Dictionary containing rule execution results

**Example**:
```python
from aws_main_rule_exec import lambda_handler

result = lambda_handler(event, context)
```

### Configuration Utilities

#### `rules_set_cfg_read() -> List[Dict[str, Any]]`

Read and parse rules configuration (cached).

#### `actions_set_cfg_read() -> Dict[str, Any]`

Read and parse actions/patterns configuration (cached).

#### `rules_set_setup(rules_set: List[Dict[str, Any]]) -> List[Dict[str, Any]]`

Set up rules by loading conditions and preparing for execution.

### Rule Utilities

#### `rule_run(rule: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]`

Execute a single rule against data.

**Parameters**:
- `rule`: Rule dictionary
- `data`: Input data dictionary

**Returns**:
- Dictionary with rule execution results

**Complete API Documentation**: For detailed API documentation with all functions, classes, and modules, see the [Sphinx-generated API Documentation](docs/README.md). To build the documentation:

```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install dependencies if not already installed
pip install -r requirements-dev.txt

# Build documentation
cd docs
make html
```

The HTML documentation will be generated in `docs/_build/html/`. **Note**: Ensure your virtual environment is activated and Sphinx is installed before building.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_ruleengine_exec.py

# Run with markers
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Linting
flake8 .
pylint .

# Type checking
mypy .

# Formatting
black .
```

### Project Structure

Follow the established directory structure:
- `common/`: Shared utilities
- `domain/`: Business logic and models
- `services/`: High-level services
- `tests/`: Test suite
- `config/`: Configuration files
- `data/`: Data files

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Coding standards
- Testing requirements
- Pull request process
- Development guidelines

## License

MIT License - See LICENSE file for details

## Additional Resources

- [Architecture Improvements](ARCHITECTURE_IMPROVEMENTS.md)
- [Code Organization](CODE_ORGANIZATION.md)
- [Configuration Management](CONFIGURATION_MANAGEMENT.md)
- [Production Improvements](PRODUCTION_IMPROVEMENTS.md)
- [Code Quality Backlog](CODE_QUALITY_BACKLOG.md)

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Review the documentation
- Check the code quality backlog for known improvements

---

**Version**: 1.0.0  
**Python**: 3.8+  
**Author**: Rule Engine Team
