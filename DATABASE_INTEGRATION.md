# Tiger Cloud Database Integration

This guide explains how to integrate and use Tiger Cloud (TimescaleDB/PostgreSQL) with the Rule Engine.

## Overview

The Rule Engine now supports storing rules, rulesets, conditions, actions, and execution logs in a Tiger Cloud database. This provides:

- **Persistent Storage**: Rules stored in a relational database
- **Version Control**: Track rule changes over time
- **Multi-tenancy**: Support for isolated rule sets per tenant
- **Time-Series Data**: Execution logs optimized for TimescaleDB
- **Flexible Storage**: JSON fields for flexible metadata
- **Backup & Recovery**: Database-level backups and point-in-time recovery

## Prerequisites

1. **Tiger Cloud Account**: A TimescaleDB database instance
2. **Credentials**: Database connection URL or `.env` file
3. **Python 3.8+**: Required for dependencies
4. **Virtual Environment**: Recommended for isolation

## Installation

### 1. Install Database Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install database dependencies
pip install -r requirements.txt
```

### 2. Configure Database Connection

#### Option A: Environment Variables

Set environment variables:

```bash
export USE_DATABASE=true
export TIMESCALE_SERVICE_URL="postgres://user:password@host:port/dbname?sslmode=require"

# Or use individual PostgreSQL variables
export USE_DATABASE=true
export PGHOST=your-host.timescaledb.cloud
export PGPORT=38622
export PGUSER=tsdbadmin
export PGPASSWORD=your-password
export PGDATABASE=tsdb
export PGSSLMODE=require
```

#### Option B: `.env` File

Create a `.env` file or use your Tiger Cloud credentials file:

```env
# Enable database
USE_DATABASE=true

# Database connection
TIMESCALE_SERVICE_URL=postgres://tsdbadmin:password@host:port/tsdb?sslmode=require

# Or use individual PG variables
PGHOST=your-host.timescaledb.cloud
PGPORT=38622
PGUSER=tsdbadmin
PGPASSWORD=your-password
PGDATABASE=tsdb
PGSSLMODE=require
```

### 3. Run Database Migrations

```bash
# Using the migration script
python common/db_migrations.py migrate --env-file /path/to/tiger-cloud-credentials.env

# Or using alembic directly
alembic upgrade head
```

## Database Models

### Tables

#### 1. **rulesets**
Collections of related rules with versioning support.

```sql
- id (PK)
- name (unique)
- description
- version
- status (draft, active, inactive, deprecated, archived)
- tenant_id (for multi-tenancy)
- is_default
- tags (JSON)
- metadata (JSON)
- created_at, updated_at
- created_by, updated_by
```

#### 2. **rules**
Individual business rules.

```sql
- id (PK)
- rule_id (unique business ID)
- rule_name
- attribute (data field to evaluate)
- condition (operator: equal, greater_than, etc.)
- constant (value to compare against)
- message
- weight (multiplier for scoring)
- rule_point (base points)
- priority (execution order)
- action_result (Y/N/-)
- status
- version
- ruleset_id (FK)
- tags (JSON)
- metadata (JSON)
- created_at, updated_at
```

#### 3. **conditions**
Reusable condition definitions.

```sql
- id (PK)
- condition_id (unique)
- name
- description
- attribute
- operator
- value
- status
- tags (JSON)
- metadata (JSON)
```

#### 4. **actions**
Reusable action definitions.

```sql
- id (PK)
- action_id (unique)
- name
- description
- action_type
- configuration (JSON)
- status
- tags (JSON)
- metadata (JSON)
```

#### 5. **patterns**
Action pattern mappings.

```sql
- id (PK)
- pattern_key (e.g., "YYY", "Y--")
- action_recommendation
- description
- ruleset_id (FK)
- created_at, updated_at
```

#### 6. **execution_logs**
Time-series execution logs (optimized for TimescaleDB).

```sql
- id (PK)
- execution_id
- input_data (JSON)
- output_data (JSON)
- ruleset_id
- total_points
- pattern_result
- execution_time_ms
- success
- error_message
- timestamp (indexed for time-series queries)
```

## Usage

### 1. Using Database Repository

The rule engine automatically uses the database when `USE_DATABASE=true` is set:

```python
from common.repository.config_repository import get_config_repository

# This will return DatabaseConfigRepository if USE_DATABASE=true
repo = get_config_repository()

# Read rules from database
rules = repo.read_rules_set()

# Read patterns from database
patterns = repo.read_patterns()

# Read full configuration
config = repo.read_json()
```

### 2. Creating Rulesets

```python
from common.repository.db_repository import RulesetRepository

ruleset_repo = RulesetRepository()

# Create a new ruleset
ruleset = ruleset_repo.create_ruleset(
    name="credit_scoring",
    description="Credit scoring rules for loan applications",
    version="1.0",
    is_default=True,
    tags=["finance", "credit"],
    created_by="admin"
)

print(f"Created ruleset with ID: {ruleset.id}")
```

### 3. Creating Rules

```python
from common.repository.db_repository import RuleRepository

rule_repo = RuleRepository()

# Create a rule
rule = rule_repo.create_rule(
    rule_id="CREDIT_001",
    rule_name="High Credit Score",
    attribute="credit_score",
    condition="greater_than",
    constant="700",
    ruleset_id=ruleset.id,
    weight=1.5,
    rule_point=100,
    priority=1,
    action_result="Y",
    message="Credit score is high",
    created_by="admin"
)

print(f"Created rule with ID: {rule.id}")
```

### 4. Listing Rules

```python
from common.repository.db_repository import RuleRepository

rule_repo = RuleRepository()

# List all active rules
rules = rule_repo.list_rules(status="active")

# List rules for a specific ruleset
rules = rule_repo.list_rules(ruleset_id=ruleset.id)

for rule in rules:
    print(f"{rule.rule_name}: {rule.attribute} {rule.condition} {rule.constant}")
```

### 5. Updating Rules

```python
from common.repository.db_repository import RuleRepository

rule_repo = RuleRepository()

# Update a rule
rule = rule_repo.get_rule(rule_id=1)
if rule:
    updated_rule = rule_repo.update_rule(
        rule.id,
        rule_point=150,
        weight=2.0,
        updated_by="admin"
    )
    print("Rule updated")
```

### 6. Creating Patterns

```python
from common.repository.db_repository import DatabaseConfigRepository
from common.db_connection import get_db_session
from common.db_models import Pattern

# Create patterns for a ruleset
with get_db_session() as session:
    pattern = Pattern(
        pattern_key="YYY",
        action_recommendation="Approved",
        description="All three rules matched",
        ruleset_id=ruleset.id
    )
    session.add(pattern)

    pattern2 = Pattern(
        pattern_key="Y--",
        action_recommendation="Rejected",
        description="Only first rule matched",
        ruleset_id=ruleset.id
    )
    session.add(pattern2)

print("Patterns created")
```

## Switching Between Storage Backends

The rule engine supports multiple storage backends. Priority order:

1. **Database** (if `USE_DATABASE=true` and `DATABASE_URL` is set)
2. **S3** (if `S3_BUCKET` is set)
3. **File System** (default)

### Example: Switch to File Storage

```bash
# Disable database, use file storage
export USE_DATABASE=false
export RULES_CONFIG_PATH=data/input/rules_config.json
```

### Example: Switch to S3 Storage

```bash
# Disable database, use S3
export USE_DATABASE=false
export S3_BUCKET=my-rule-config-bucket
```

### Example: Use Database

```bash
# Enable database
export USE_DATABASE=true
export TIMESCALE_SERVICE_URL=postgres://...
```

## Database Maintenance

### Running Migrations

```bash
# Upgrade to latest migration
python common/db_migrations.py migrate

# Using alembic directly
alembic upgrade head

# Check current version
alembic current

# Show migration history
alembic history
```

### Resetting Database (Development Only)

⚠️ **WARNING**: This will delete all data!

```bash
# Drop all tables and recreate schema
python common/db_migrations.py reset

# Or individual commands
python common/db_migrations.py drop-tables
python common/db_migrations.py create-schema
```

### Backup and Restore

#### Backup

```bash
# Backup database to SQL file
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Using environment variables
pg_dump $TIMESCALE_SERVICE_URL > backup.sql
```

#### Restore

```bash
# Restore from backup
psql $DATABASE_URL < backup_20250201.sql
```

### Performance Monitoring

TimescaleDB provides built-in monitoring:

```sql
-- Check table sizes
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check execution log count
SELECT COUNT(*) FROM execution_logs;

-- Check recent executions
SELECT * FROM execution_logs
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

## API Endpoints (Future)

The following API endpoints will be added for database management:

### Rulesets

- `POST /api/v1/rulesets` - Create ruleset
- `GET /api/v1/rulesets` - List rulesets
- `GET /api/v1/rulesets/{id}` - Get ruleset
- `PUT /api/v1/rulesets/{id}` - Update ruleset
- `DELETE /api/v1/rulesets/{id}` - Delete ruleset

### Rules

- `POST /api/v1/rules` - Create rule
- `GET /api/v1/rules` - List rules
- `GET /api/v1/rules/{id}` - Get rule
- `PUT /api/v1/rules/{id}` - Update rule
- `DELETE /api/v1/rules/{id}` - Delete rule

### Execution Logs

- `GET /api/v1/execution-logs` - List execution logs
- `GET /api/v1/execution-logs/{id}` - Get execution log details

## Troubleshooting

### Connection Issues

```bash
# Test database connection
python common/db_connection.py --env-file /path/to/credentials.env

# Check environment variables
echo $USE_DATABASE
echo $TIMESCALE_SERVICE_URL
```

### Migration Issues

```bash
# Check alembic status
alembic status

# View migration errors
alembic upgrade head --sql
```

### SSL Issues

If you get SSL errors, ensure `sslmode=require` is in your connection URL:

```env
TIMESCALE_SERVICE_URL=postgres://user:pass@host:port/db?sslmode=require
```

## Best Practices

1. **Use Connection Pooling**: The default configuration uses connection pooling for efficiency
2. **Index Optimization**: Database indexes are automatically created on frequently queried columns
3. **Time-Series Data**: Execution logs are indexed by timestamp for efficient time-range queries
4. **Multi-tenancy**: Use `tenant_id` field to isolate rulesets per tenant
5. **Versioning**: Always update the `version` field when modifying rules
6. **Status Management**: Use status fields to manage rule lifecycle (draft → active → deprecated)

## Migration from File/S3

### Migrate from JSON Files

```python
import json
from common.repository.db_repository import RulesetRepository, RuleRepository

# Load existing JSON config
with open('data/input/rules_config_v4.json', 'r') as f:
    config = json.load(f)

# Create ruleset
ruleset_repo = RulesetRepository()
ruleset = ruleset_repo.create_ruleset(
    name="migrated_rules",
    description="Migrated from JSON config",
    version="1.0",
    is_default=True
)

# Migrate rules
rule_repo = RuleRepository()
for rule_data in config.get('rules_set', []):
    rule_repo.create_rule(
        rule_id=rule_data['id'],
        rule_name=rule_data['rule_name'],
        attribute=rule_data['attribute'],
        condition=rule_data['condition'],
        constant=rule_data['constant'],
        message=rule_data.get('message'),
        weight=rule_data.get('weight', 1.0),
        rule_point=rule_data.get('rule_point', 0),
        priority=rule_data.get('priority', 0),
        action_result=rule_data['action_result'],
        ruleset_id=ruleset.id
    )

print(f"Migrated {len(config.get('rules_set', []))} rules to database")
```

## Additional Resources

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Migration Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
