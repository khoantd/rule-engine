# Tiger Cloud Database Integration - Quick Start

## What Was Implemented

✅ **Complete database integration for Tiger Cloud (TimescaleDB/PostgreSQL)**

### Files Created

1. **Database Connection**: `common/db_connection.py`
   - Connection pooling
   - Session management
   - Connection testing
   - Environment variable loading

2. **Database Models**: `common/db_models.py`
   - Ruleset, Rule, Condition, Action, Pattern models
   - ExecutionLog for time-series data
   - SQLAlchemy ORM with relationships
   - JSON fields for flexible metadata

3. **Database Repository**: `common/repository/db_repository.py`
   - `DatabaseConfigRepository` - Compatible with existing repo pattern
   - `RulesetRepository` - CRUD for rulesets
   - `RuleRepository` - CRUD for rules
   - `ConditionRepository` - CRUD for conditions
   - `ActionRepository` - CRUD for actions

4. **Migrations**:
   - `migrations/env.py` - Alembic configuration
   - `migrations/versions/2025.02.01_00.00_001_initial_schema.py` - Initial schema
   - `common/db_migrations.py` - Migration utilities
   - `alembic.ini` - Alembic configuration

5. **Setup Scripts**:
   - `setup_database.py` - One-command setup with sample data
   - `DATABASE_INTEGRATION.md` - Complete documentation

6. **Configuration Updates**:
   - `requirements.txt` - Added database dependencies
   - `common/config.py` - Database configuration support
   - `common/repository/config_repository.py` - Auto-detect database backend

### Database Schema

```
rulesets (ruleset collections)
├── id, name, description, version, status
├── tenant_id (multi-tenancy)
└── rules (one-to-many)

rules (business rules)
├── id, rule_id, rule_name, attribute
├── condition, constant, message
├── weight, rule_point, priority
├── action_result, status, version
└── ruleset_id (FK)

conditions (reusable conditions)
├── id, condition_id, name
├── attribute, operator, value
└── status

actions (reusable actions)
├── id, action_id, name
├── action_type, configuration (JSON)
└── status

patterns (action mappings)
├── id, pattern_key, action_recommendation
├── description
└── ruleset_id (FK)

execution_logs (time-series)
├── id, execution_id
├── input_data (JSON), output_data (JSON)
├── ruleset_id, total_points, pattern_result
├── execution_time_ms, success, error_message
└── timestamp (indexed)
```

## Quick Start Guide

### 1. Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Database

**Option A: Quick Setup (Recommended)**

```bash
# Run complete setup with sample data
python3 setup_database.py --env-file /Users/macbook/Downloads/tiger-cloud-db-29014-credentials.env
```

This will:
- Test database connection
- Create database schema
- Create sample ruleset with 3 rules
- Create 4 patterns
- Verify setup

**Option B: Manual Setup**

```bash
# 1. Test connection
python3 common/db_connection.py --env-file /Users/macbook/Downloads/tiger-cloud-db-29014-credentials.env

# 2. Create schema
python3 common/db_migrations.py create-schema --env-file /Users/macbook/Downloads/tiger-cloud-db-29014-credentials.env

# 3. Create sample data using Python script
# (See DATABASE_INTEGRATION.md for examples)
```

### 3. Use Database Storage

Set environment variable:

```bash
export USE_DATABASE=true
```

The rule engine will now automatically use database storage!

```python
from common.repository.config_repository import get_config_repository

# Get repository (will be DatabaseConfigRepository)
repo = get_config_repository()

# Read rules from database
rules = repo.read_rules_set()
patterns = repo.read_patterns()
```

### 4. Create Your Own Rules

```python
from common.repository.db_repository import RulesetRepository, RuleRepository
from common.db_connection import get_db_session
from common.db_models import Pattern

# Create ruleset
ruleset_repo = RulesetRepository()
ruleset = ruleset_repo.create_ruleset(
    name="my_rules",
    description="My custom rules",
    is_default=True,
    created_by="user"
)

# Create rule
rule_repo = RuleRepository()
rule = rule_repo.create_rule(
    rule_id="MY_RULE_001",
    rule_name="My First Rule",
    attribute="age",
    condition="greater_than",
    constant="25",
    ruleset_id=ruleset.id,
    rule_point=100,
    priority=1,
    action_result="Y",
    created_by="user"
)

# Create pattern
with get_db_session() as session:
    pattern = Pattern(
        pattern_key="Y",
        action_recommendation="Approved",
        description="Single rule matched",
        ruleset_id=ruleset.id
    )
    session.add(pattern)

print(f"Created rule with ID: {rule.id}")
```

## Next Steps

### Testing the Integration

```python
# Test database integration
from services.ruleengine_exec import rules_exec

# This will read rules from database (if USE_DATABASE=true)
data = {'score': 85}
result = rules_exec(data)

print(f"Total points: {result['total_points']}")
print(f"Pattern: {result['pattern_result']}")
print(f"Action: {result['action_recommendation']}")
```

### Switching Back to File/S3 Storage

```bash
# Disable database
export USE_DATABASE=false

# Use file storage (default)
# or
export S3_BUCKET=my-bucket  # Use S3 storage
```

### Adding API Endpoints (Optional)

The foundation is ready for CRUD API endpoints. See `DATABASE_INTEGRATION.md` for planned endpoints.

## Documentation

- **Complete Guide**: See `DATABASE_INTEGRATION.md`
- **Database Models**: See `common/db_models.py`
- **Repository Pattern**: See `common/repository/db_repository.py`
- **Connection Utilities**: See `common/db_connection.py`

## Troubleshooting

**Connection Issues:**
```bash
# Test connection
python3 setup_database.py --test-only --env-file /path/to/credentials.env
```

**Module Not Found:**
```bash
# Install dependencies
pip install -r requirements.txt
```

**Migration Issues:**
```bash
# Reset database (will delete all data!)
python3 common/db_migrations.py reset --env-file /path/to/credentials.env
```

## Support

For issues or questions:
1. Check `DATABASE_INTEGRATION.md` for detailed documentation
2. Review error logs in `common/logger.py` output
3. Verify environment variables are set correctly
4. Test database connection with the test script

## Summary

✅ Database models created (Ruleset, Rule, Condition, Action, Pattern, ExecutionLog)
✅ Repository implementation compatible with existing code
✅ Migration scripts for schema management
✅ Setup script with sample data
✅ Complete documentation
✅ Auto-detection of storage backend (File/S3/Database)

**The integration is complete and ready to use!** Just install dependencies and run the setup script.
