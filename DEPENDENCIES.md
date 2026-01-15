# Dependencies & Environment Management

This document describes the dependency management strategy and environment setup for the Rule Engine codebase.

## Python Version Requirements

- **Minimum Version**: Python 3.8
- **Recommended Version**: Python 3.9 or higher
- **Tested Versions**: Python 3.8, 3.9, 3.10, 3.11
- **Current Development**: Python 3.11

### Python Version Files

- **`.python-version`**: Specifies Python 3.8 (for pyenv and similar tools)
- **`pyproject.toml`**: `requires-python = ">=3.8"` (for pip and build tools)
- **`mypy.ini`**: `python_version = 3.8` (for type checking)

## Dependency Files

### Production Dependencies (`requirements.txt`)

Contains pinned versions of production dependencies:

```txt
rule_engine==4.1.0
jsonpath_ng==1.5.3
dataclasses-json==0.6.6
```

**Installation**:
```bash
pip install -r requirements.txt
```

### Development Dependencies (`requirements-dev.txt`)

Contains development and testing dependencies:

- **Testing**: pytest, pytest-cov, pytest-mock, pytest-xdist
- **Code Quality**: pylint, flake8, black, mypy, ruff
- **Test Utilities**: freezegun, responses, moto
- **Documentation**: sphinx, sphinx-rtd-theme

**Installation**:
```bash
pip install -r requirements-dev.txt
```

### Modern Dependency Management (`pyproject.toml`)

The project uses `pyproject.toml` for modern Python packaging:

- **Project Metadata**: Name, version, description, license
- **Dependencies**: Production dependencies
- **Optional Dependencies**: Development dependencies as `dev` extra
- **Tool Configuration**: Black, mypy, pylint, pytest

**Installation**:
```bash
# Production dependencies
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

## Dependency Management Strategy

### Version Pinning

All production dependencies are pinned to specific versions:

```txt
package==X.Y.Z
```

**Benefits**:
- ✅ Reproducible builds
- ✅ Consistent environments
- ✅ Predictable behavior
- ✅ Easier debugging

### Minimum Versions

Some dependencies use minimum version specifiers in `pyproject.toml`:

```toml
dependencies = [
    "rule-engine>=4.1.0",
    "jsonpath-ng>=1.5.3",
    "dataclasses-json>=0.6.6",
]
```

**Use Case**: For build metadata while maintaining pinning in `requirements.txt`

### Development Dependencies

Development dependencies are separated into `requirements-dev.txt` and `pyproject.toml` optional dependencies.

**Rationale**:
- Production deployments don't need test tools
- Smaller production image size
- Clear separation of concerns

## Production Dependencies

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `rule-engine` | `4.1.0` | Rule evaluation engine |
| `jsonpath-ng` | `1.5.3` | JSONPath parsing |
| `dataclasses-json` | `0.6.6` | JSON serialization for dataclasses |

### Dependency Details

#### rule-engine

**Version**: 4.1.0
**Purpose**: Core rule evaluation engine
**Usage**: Used in `common/rule_engine_util.py` for rule evaluation
**Documentation**: https://pypi.org/project/rule-engine/

#### jsonpath-ng

**Version**: 1.5.3
**Purpose**: JSONPath expression parsing
**Usage**: Used in `common/json_util.py` for JSON parsing
**Documentation**: https://pypi.org/project/jsonpath-ng/

#### dataclasses-json

**Version**: 0.6.6
**Purpose**: JSON serialization for Python dataclasses
**Usage**: Used for domain model serialization
**Documentation**: https://pypi.org/project/dataclasses-json/

## Development Dependencies

### Testing Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | `7.4.3` | Testing framework |
| `pytest-cov` | `4.1.0` | Coverage plugin |
| `pytest-mock` | `3.12.1` | Mocking utilities |
| `pytest-xdist` | `3.5.0` | Parallel test execution |
| `coverage` | `7.3.4` | Code coverage tool |
| `freezegun` | `1.2.2` | Time mocking |
| `responses` | `0.24.1` | HTTP mocking |
| `moto` | `4.2.14` | AWS mocking |

### Code Quality Tools

| Package | Version | Purpose |
|---------|---------|---------|
| `pylint` | `3.0.2` | Linter |
| `flake8` | `6.1.0` | Style checker |
| `black` | `23.12.1` | Code formatter |
| `mypy` | `1.7.1` | Type checker |
| `ruff` | `0.1.9` | Fast linter |

### Documentation Tools

| Package | Version | Purpose |
|---------|---------|---------|
| `sphinx` | `7.2.6` | Documentation generator |
| `sphinx-rtd-theme` | `2.0.0` | Read the Docs theme |

## Virtual Environment Setup

### Creating Virtual Environment

```bash
# Using venv (recommended)
python3 -m venv venv

# Using pyenv (if managing Python versions)
pyenv local 3.8
python -m venv venv
```

### Activating Virtual Environment

**macOS/Linux**:
```bash
source venv/bin/activate
```

**Windows**:
```bash
venv\Scripts\activate
```

### Installing Dependencies

```bash
# Activate virtual environment first
source venv/bin/activate

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Or install with extras
pip install -e ".[dev]"
```

## Dependency Updates

### Updating Dependencies

1. **Check for updates**:
   ```bash
   pip list --outdated
   ```

2. **Update specific package**:
   ```bash
   pip install --upgrade package_name
   ```

3. **Update requirements.txt**:
   ```bash
   pip freeze > requirements.txt
   ```
   **Note**: Review and edit manually to keep pinned versions

4. **Test after updates**:
   ```bash
   pytest
   ```

### Version Update Process

1. **Identify package to update**
2. **Check changelog** for breaking changes
3. **Update in test environment first**
4. **Run full test suite**
5. **Update `requirements.txt`** with new version
6. **Update `pyproject.toml`** if needed
7. **Document changes** in commit message

## Dependency Conflicts

### Checking for Conflicts

```bash
pip check
```

### Resolving Conflicts

1. **Identify conflicting packages**
2. **Check compatibility**:
   - Review package documentation
   - Check version compatibility matrix
3. **Update conflicting packages** to compatible versions
4. **Test thoroughly** after resolution

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.8'

- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

- name: Run tests
  run: pytest
```

## Environment Variables

### Development Environment

Set these variables for local development:

```bash
# AWS Configuration (if using AWS services)
export AWS_REGION=us-east-1
export AWS_PROFILE=default

# Logging
export LOG_LEVEL=DEBUG

# Configuration
export CONFIG_PATH=config/config.ini
```

### Production Environment

Use environment variables or secrets management:
- AWS Secrets Manager
- Environment variables
- Configuration files (secure storage)

## Best Practices

### 1. Always Use Virtual Environments

Never install packages globally. Always use a virtual environment.

### 2. Pin Production Dependencies

Use exact versions (`==`) for production dependencies to ensure reproducibility.

### 3. Separate Development Dependencies

Keep development dependencies separate from production dependencies.

### 4. Regular Updates

Regularly update dependencies for security patches and bug fixes.

### 5. Test After Updates

Always run tests after updating dependencies to catch compatibility issues.

### 6. Document Changes

Document dependency updates in commit messages and changelog.

### 7. Use Requirements Files

Always maintain `requirements.txt` and `requirements-dev.txt` files.

### 8. Version Control

Commit dependency files to version control for team consistency.

## Troubleshooting

### Import Errors

If you encounter import errors:

1. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Reinstall dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Check Python path**:
   ```python
   import sys
   print(sys.path)
   ```

### Version Conflicts

If you encounter version conflicts:

1. **Check installed versions**:
   ```bash
   pip list
   ```

2. **Check for conflicts**:
   ```bash
   pip check
   ```

3. **Resolve conflicts** by updating packages to compatible versions

### Missing Dependencies

If dependencies are missing:

1. **Check requirements files** are present
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Summary

The Rule Engine uses:

- ✅ **Pinned versions** for production dependencies
- ✅ **Separate development dependencies**
- ✅ **Modern packaging** with `pyproject.toml`
- ✅ **Python 3.8+** minimum requirement
- ✅ **Virtual environments** for isolation
- ✅ **Clear documentation** for dependency management

For questions or issues, refer to this documentation or contact the development team.

