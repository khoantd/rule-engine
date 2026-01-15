# Installation Troubleshooting Guide

This guide helps resolve common installation issues with the Rule Engine.

## Dependency Conflicts

### Error: "pip's dependency resolver does not currently take into account all the packages"

This error occurs when installing into a Python environment that already has conflicting packages.

#### Root Causes:

1. **Installing into system Python**: Installing directly into system Python mixes dependencies from different projects
2. **Conflicting versions**: Other packages (streamlit, copier, docling, etc.) require different versions of shared dependencies
3. **Not using virtual environment**: All packages are installed globally, causing conflicts

#### Solutions:

**Solution 1: Use Virtual Environment (Recommended)**

Always use a virtual environment to isolate dependencies:

```bash
# From project root
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

**Solution 2: Fix System Python Conflicts**

If you must use system Python (not recommended), upgrade conflicting packages:

```bash
# Upgrade conflicting packages
pip install --upgrade rich>=14.1.0 jinja2>=3.1.3 requests>=2.32.2

# Then install project dependencies
pip install -r requirements.txt
```

**Note**: This may break other projects using these packages.

**Solution 3: Use pip with --ignore-installed**

Force installation ignoring existing packages (risky):

```bash
pip install --ignore-installed -r requirements.txt
```

**Warning**: This may break other applications.

### Specific Dependency Conflicts

#### 1. Rich Version Conflict

**Error**: `streamlit 1.39.0 requires rich<14,>=10.14.0, but you have rich 14.1.0`

**Cause**: streamlit needs rich <14, but newer version (14.1.0) is installed.

**Fix**: Use virtual environment to isolate dependencies.

#### 2. Jinja2 Version Conflict

**Error**: `copier 9.2.0 requires jinja2>=3.1.3, but you have jinja2 3.1.2`

**Cause**: copier needs jinja2 >=3.1.3, but older version (3.1.2) is installed.

**Fix**:
```bash
# In virtual environment
pip install --upgrade jinja2>=3.1.3
```

#### 3. Requests Version Conflict

**Error**: `docling 2.25.0 requires requests<3.0.0,>=2.32.2, but you have requests 2.31.0`

**Cause**: docling needs requests >=2.32.2, but older version (2.31.0) is installed.

**Fix**:
```bash
# In virtual environment
pip install --upgrade "requests>=2.32.2,<3.0.0"
```

## Virtual Environment Best Practices

### Creating Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Verify Python version (should be 3.8+)
python --version
```

### Activating Virtual Environment

**macOS/Linux**:
```bash
source .venv/bin/activate
```

**Windows**:
```cmd
.venv\Scripts\activate
```

**PowerShell**:
```powershell
.venv\Scripts\Activate.ps1
```

### Deactivating Virtual Environment

```bash
deactivate
```

### Verifying Virtual Environment

Check that you're using the virtual environment Python:

```bash
which python    # Should point to .venv/bin/python
python --version
pip list         # Should show only installed packages
```

## Clean Installation

If you have conflicts, perform a clean installation:

```bash
# Remove existing virtual environment
rm -rf .venv

# Create fresh virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Verification

After installation, verify everything works:

```bash
# Check Python version
python --version  # Should be 3.8+

# Check installed packages
pip list | grep -E "(rule-engine|jsonpath|dataclasses)"

# Test imports
python -c "from services.ruleengine_exec import rules_exec; print('OK')"
```

## Common Issues

### Issue: "Module not found" after installation

**Cause**: Virtual environment not activated or dependencies not installed.

**Fix**:
```bash
# Activate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Permission denied" when installing

**Cause**: Trying to install into system Python without sudo.

**Fix**: Always use virtual environment (no sudo needed).

### Issue: Wrong Python version

**Cause**: Virtual environment created with wrong Python version.

**Fix**:
```bash
# Remove old venv
rm -rf .venv

# Create with specific Python version
python3.8 -m venv .venv  # or python3.9, python3.10, etc.

# Activate
source .venv/bin/activate
```

## Production Deployment

For production, use the same approach:

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install only production dependencies
pip install -r requirements.txt

# Verify
python -c "from services.ruleengine_exec import rules_exec; print('OK')"
```

## Getting Help

If issues persist:

1. Check Python version: `python --version` (must be 3.8+)
2. Verify virtual environment is activated: `which python`
3. Check installed packages: `pip list`
4. Review error messages carefully
5. Check this troubleshooting guide
6. Open an issue with error details

