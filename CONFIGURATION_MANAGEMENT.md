# Configuration Management

This document describes the configuration management strategy for the Rule Engine codebase.

## Overview

The Rule Engine uses a centralized configuration management system that supports:
- Environment variables (preferred for production)
- Configuration files (INI format for local development)
- AWS Systems Manager Parameter Store (for secrets in production)
- AWS Secrets Manager (alternative for secrets)

## Configuration Sources

### Priority Order

Configuration values are loaded in the following priority order:

1. **Environment Variables** (highest priority)
2. **Config File** (`config/config.ini`)
3. **Default Values** (fallback)

### Secrets Management

For production, secrets should be loaded from:
- **AWS Systems Manager Parameter Store** (recommended)
- **AWS Secrets Manager** (alternative)

**Never store secrets in configuration files or environment variables in production.**

## Configuration Class

### Location

The main configuration class is `common.config.Config`:

```python
from common.config import get_config

config = get_config()
```

### Configuration Properties

#### Environment

```python
config.environment  # 'dev', 'staging', or 'prod'
```

**Environment Variables**:
- `ENVIRONMENT` (default: 'dev')

#### File Paths

```python
config.rules_config_path      # Path to rules configuration
config.conditions_config_path # Path to conditions configuration
```

**Environment Variables**:
- `RULES_CONFIG_PATH` (default: 'data/input/rules_config_v4.json')
- `CONDITIONS_CONFIG_PATH` (default: 'data/input/conditions_config.json')

#### AWS Configuration

```python
config.aws_region          # AWS region
config.s3_bucket           # S3 bucket name (optional)
config.s3_config_prefix   # S3 config prefix
```

**Environment Variables**:
- `AWS_REGION` (default: 'us-east-1')
- `S3_BUCKET` (for S3 bucket name)
- `S3_BUCKET_RULE_CONFIG` (legacy, for backward compatibility)
- `S3_CONFIG_PREFIX` (default: 'config/')

#### Logging

```python
config.log_level  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

**Environment Variables**:
- `LOG_LEVEL` (default: 'INFO')

#### Performance

```python
config.cache_ttl    # Cache time-to-live in seconds
config.max_retries  # Maximum retry attempts
```

**Environment Variables**:
- `CACHE_TTL` (default: 3600)
- `MAX_RETRIES` (default: 3)

## Using Configuration

### Getting Configuration

```python
from common.config import get_config

# Get global configuration instance
config = get_config()

# Access configuration values
bucket = config.s3_bucket
region = config.aws_region
log_level = config.log_level
```

### Configuration Validation

The configuration is automatically validated when loaded:

```python
config = get_config()  # Automatically validates
config.validate()      # Manual validation if needed
```

**Validation Checks**:
- Environment must be 'dev', 'staging', or 'prod'
- File paths must exist (for local files)
- Log level must be valid
- AWS region format must be valid
- Cache TTL must be positive
- Max retries must be positive
- Security validation in production

### Environment-Specific Configuration

```python
config = get_config()

if config.is_production():
    # Production-specific logic
    pass

if config.is_development():
    # Development-specific logic
    pass
```

## Configuration Files

### Config File Format

Configuration is stored in `config/config.ini` (INI format):

```ini
[RULE]
file_name = data/input/rules_config_v4.json

[CONDITIONS]
file_name = data/input/conditions_config.json

[JIRA]
url = https://your-jira-instance.atlassian.net
username = your-username
# token should be loaded from secrets manager, not from file
```

**Note**: Do not store secrets in the config file. Use secrets manager in production.

### Loading from File

```python
from common.config import Config

# Load from file
config = Config.from_file('config/config.ini')

# Load from environment (preferred)
config = Config.from_env()
```

## Environment Variables

### Required Environment Variables

For production deployments, set these environment variables:

```bash
# Environment
export ENVIRONMENT=prod

# AWS Configuration
export AWS_REGION=us-east-1
export S3_BUCKET=your-config-bucket

# File Paths
export RULES_CONFIG_PATH=s3://your-bucket/config/rules_config.json
export CONDITIONS_CONFIG_PATH=s3://your-bucket/config/conditions_config.json

# Logging
export LOG_LEVEL=INFO

# Performance
export CACHE_TTL=3600
export MAX_RETRIES=3
```

### Optional Environment Variables

```bash
# S3 Configuration (legacy, for backward compatibility)
export S3_BUCKET_RULE_CONFIG=your-config-bucket
export S3_CONFIG_PREFIX=config/

# Configuration File Path
export CONFIG_FILE_PATH=config/config.ini
```

## Secrets Management

### AWS Systems Manager Parameter Store

For production, secrets should be stored in AWS SSM Parameter Store:

```bash
# Store secret
aws ssm put-parameter \
    --name /rule-engine/jira_token \
    --value "your-token" \
    --type SecureString

# Load secret in application
export USE_SSM=true
export SSM_PREFIX=/rule-engine/
```

### AWS Secrets Manager

Alternatively, use AWS Secrets Manager:

```python
from common.secrets_manager import get_secrets_manager

secrets_manager = get_secrets_manager()
token = secrets_manager.get_secret('jira_token')
```

## Configuration Caching

Configuration is automatically cached for performance:

### File-Based Configuration

The `common.util.cfg_read()` function uses memoization with file change detection:

```python
from common.util import cfg_read

# First call reads from file
value = cfg_read('RULE', 'file_name')

# Subsequent calls use cache (unless file changes)
value = cfg_read('RULE', 'file_name')
```

**Caching Behavior**:
- ✅ Cached after first read
- ✅ Automatically invalidated when file changes
- ✅ Per-section/parameter caching

### Configuration Class

The `Config` class is cached as a singleton:

```python
from common.config import get_config

# First call loads and caches
config = get_config()

# Subsequent calls return cached instance
config = get_config()  # Returns same instance
```

## Hot Reloading

### Manual Reloading

To reload configuration:

```python
from common.config import set_config, Config

# Reload configuration
new_config = Config.from_env()
set_config(new_config)
```

### Automatic Reloading

For file-based configuration, changes are automatically detected:

- File modification time is checked
- Cache is invalidated when file changes
- Next read loads fresh values

**Note**: Environment variable changes require application restart.

## Migration Guide

### From Hard-coded Values

**Old Code** (Hard-coded):
```python
bucket = 'rule-config-file'
config_file = 'config/config.ini'
```

**New Code** (Configuration-based):
```python
from common.config import get_config

config = get_config()
bucket = config.s3_bucket
config_file = 'config/config.ini'  # Or use CONFIG_FILE_PATH env var
```

### From Direct os.getenv

**Old Code**:
```python
bucket = os.getenv('S3_BUCKET_RULE_CONFIG', 'rule-config-file')
```

**New Code**:
```python
from common.config import get_config

config = get_config()
bucket = config.s3_bucket  # Uses S3_BUCKET env var, with fallback
```

## Best Practices

### 1. Use Environment Variables for Production

```bash
# Production
export S3_BUCKET=prod-config-bucket
export ENVIRONMENT=prod
export LOG_LEVEL=INFO
```

### 2. Use Config Files for Development

```ini
# config/config.ini
[RULE]
file_name = data/input/rules_config_v4.json
```

### 3. Never Store Secrets in Files

```python
# ❌ Bad: Hard-coded secret
token = "abc123"

# ❌ Bad: Secret in config file
# config.ini
# token = abc123

# ✅ Good: Load from secrets manager
from common.secrets_manager import get_secrets_manager
secrets = get_secrets_manager()
token = secrets.get_secret('jira_token')
```

### 4. Validate Configuration

```python
config = get_config()
config.validate()  # Validates configuration values
```

### 5. Use Type-Safe Access

```python
# ✅ Good: Type-safe access
config = get_config()
bucket: Optional[str] = config.s3_bucket

# ❌ Bad: Direct os.getenv without type hints
bucket = os.getenv('S3_BUCKET')
```

### 6. Handle Missing Configuration Gracefully

```python
from common.config import get_config

config = get_config()

# Provide defaults for optional configuration
bucket = config.s3_bucket or 'default-bucket'
```

## Configuration Repository

The configuration repository pattern provides abstraction over storage:

```python
from common.repository import get_config_repository

repo = get_config_repository()

# Read configuration from repository (file or S3)
rules = repo.read_rules_set('data/input/rules_config.json')
```

**Repository Selection**:
- **File Repository**: Used when `s3_bucket` is not configured
- **S3 Repository**: Used when `s3_bucket` is configured

## Troubleshooting

### Configuration Not Loading

1. **Check Environment Variables**:
   ```bash
   echo $ENVIRONMENT
   echo $S3_BUCKET
   ```

2. **Check Config File**:
   ```bash
   cat config/config.ini
   ```

3. **Check Configuration Validation**:
   ```python
   from common.config import get_config
   config = get_config()
   config.validate()  # Will raise ConfigurationError if invalid
   ```

### Configuration Cache Issues

1. **Clear Cache**:
   ```python
   from common.cache import get_file_cache
   cache = get_file_cache()
   cache.clear()
   ```

2. **Reload Configuration**:
   ```python
   from common.config import set_config, Config
   set_config(Config.from_env())
   ```

### Secrets Not Loading

1. **Check Secrets Manager**:
   ```python
   from common.secrets_manager import get_secrets_manager
   secrets = get_secrets_manager()
   token = secrets.get_secret('jira_token')
   ```

2. **Check Environment Variables**:
   ```bash
   echo $USE_SSM
   echo $SSM_PREFIX
   ```

## Summary

Configuration Management provides:

- ✅ **Centralized Configuration**: Single source of truth
- ✅ **Environment-Based**: Support for dev, staging, prod
- ✅ **Type-Safe Access**: Config class with type hints
- ✅ **Secrets Management**: Integration with AWS services
- ✅ **Configuration Validation**: Automatic validation on load
- ✅ **Caching**: Performance optimization with automatic invalidation
- ✅ **Hot Reloading**: Automatic detection of file changes

For questions or issues, refer to this documentation or contact the development team.

