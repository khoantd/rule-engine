# Rule Versioning & A/B Testing Engine

This document describes the Rule Versioning & A/B Testing Engine implementation for the Rule Engine.

## Overview

The Rule Versioning & A/B Testing Engine provides:

1. **Rule Versioning**: Track all changes to rules, support rollbacks, and compare versions
2. **A/B Testing**: Run controlled experiments to compare different rule versions

## Architecture

### Database Models

#### RuleVersion
Stores historical versions of rules for rollback and comparison.

**Key Features:**
- Automatic version creation on rule updates
- Tracks complete rule state snapshot
- Supports version comparison
- Current version tracking

**Fields:**
- `id`: Primary key
- `version_number`: Incremental version number
- `rule_id`: Rule identifier
- `rule_snapshot`: Complete rule state (name, condition, constant, etc.)
- `is_current`: Marks if this is the current active version
- `change_reason`: Reason for the change
- `created_by`: User who created the version

#### RuleABTest
Manages A/B test configurations for comparing rule versions.

**Key Features:**
- Configurable traffic splits
- Test timing controls
- Statistical significance tracking
- Variant descriptions

**Fields:**
- `id`: Primary key
- `test_id`: Unique test identifier
- `rule_id`: Target rule ID
- `variant_a_version`: Version string for variant A (control)
- `variant_b_version`: Version string for variant B (treatment)
- `traffic_split_a/b`: Traffic distribution (default: 0.5/0.5)
- `status`: Test status (draft, running, completed)
- `start_time/end_time`: Test duration control
- `min_sample_size`: Minimum samples per variant
- `confidence_level`: Statistical confidence (default: 0.95)
- `winning_variant`: Declared winner after test completion

#### TestAssignment
Tracks which users/requests are assigned to which A/B test variant.

**Key Features:**
- Hash-based consistent assignment
- Execution tracking
- Assignment key persistence

**Fields:**
- `id`: Primary key
- `ab_test_id`: Foreign key to RuleABTest
- `assignment_key`: User/session/request ID for assignment
- `variant`: Assigned variant ('A' or 'B')
- `execution_count`: Number of executions with this assignment
- `last_execution_at`: Timestamp of last execution

## Services

### RuleVersioningService

**Location:** `services/rule_versioning.py`

**Key Methods:**

#### `create_version(rule, change_reason, created_by)`
Creates a new version of a rule automatically when a rule is updated.

**Example:**
```python
service = get_rule_versioning_service()
version = service.create_version(
    rule=rule,
    change_reason="Updated threshold value",
    created_by="user123"
)
```

#### `get_version_history(rule_id, limit)`
Retrieves version history for a rule.

**Example:**
```python
history = service.get_version_history(rule_id="risk_rule_1", limit=10)
```

#### `rollback_to_version(rule_id, version_number, change_reason)`
Rolls back a rule to a specific version.

**Example:**
```python
service.rollback_to_version(
    rule_id="risk_rule_1",
    version_number=3,
    change_reason="Rollback due to increased false positives"
)
```

#### `compare_versions(rule_id, version_a, version_b)`
Compares two versions to show differences.

**Example:**
```python
comparison = service.compare_versions(
    rule_id="risk_rule_1",
    version_a=3,
    version_b=4
)
# Returns differences in fields: rule_name, attribute, condition, constant, etc.
```

### ABTestingService

**Location:** `services/ab_testing.py`

**Key Methods:**

#### `create_test(...)`
Creates a new A/B test.

**Example:**
```python
service = get_ab_testing_service()
test = service.create_test(
    test_id="test_risk_threshold_v2",
    test_name="Test new risk threshold",
    rule_id="risk_rule_1",
    ruleset_id=1,
    variant_a_version="1.0",
    variant_b_version="2.0",
    traffic_split_a=0.5,
    traffic_split_b=0.5,
    duration_hours=168,  # 1 week
    min_sample_size=1000,
    confidence_level=0.95
)
```

#### `start_test(test_id, started_by)`
Starts a draft A/B test.

**Example:**
```python
service.start_test(test_id="test_risk_threshold_v2", started_by="user123")
```

#### `stop_test(test_id, winning_variant, stopped_by)`
Stops a running test and optionally declares a winner.

**Example:**
```python
service.stop_test(
    test_id="test_risk_threshold_v2",
    winning_variant="B",
    stopped_by="user123"
)
```

#### `assign_variant(test_id, assignment_key)`
Assigns an assignment key to a variant using hash-based routing.

**Example:**
```python
variant = service.assign_variant(
    test_id="test_risk_threshold_v2",
    assignment_key="user_session_abc123"
)
# Returns "A" or "B"
```

#### `get_test_metrics(test_id)`
Retrieves metrics and analysis for an A/B test.

**Example:**
```python
metrics = service.get_test_metrics(test_id="test_risk_threshold_v2")
# Returns:
# {
#   "variant_a": {"assignments": 500, "metrics": {...}},
#   "variant_b": {"assignments": 500, "metrics": {...}},
#   "statistical_significance": 0.98,
#   "sample_size_met": true
# }
```

## API Endpoints

### Rule Versioning Endpoints

**Base Path:** `/api/v1/rules/versions`

| Method | Path | Description |
|---------|-------|-------------|
| GET | `/{rule_id}` | Get version history for a rule |
| GET | `/{rule_id}/current` | Get current version of a rule |
| GET | `/{rule_id}/{version_number}` | Get a specific version |
| POST | `/{rule_id}/compare` | Compare two versions |
| POST | `/{rule_id}/rollback` | Rollback to a specific version |

**Example - Get Version History:**
```bash
GET /api/v1/rules/versions/risk_rule_1?limit=10
```

**Example - Compare Versions:**
```bash
POST /api/v1/rules/versions/risk_rule_1/compare
{
  "version_a": 3,
  "version_b": 4
}
```

**Example - Rollback:**
```bash
POST /api/v1/rules/versions/risk_rule_1/rollback
{
  "version_number": 3,
  "change_reason": "Rollback due to increased false positives"
}
```

### A/B Testing Endpoints

**Base Path:** `/api/v1/rules/ab-tests`

| Method | Path | Description |
|---------|-------|-------------|
| POST | `/` | Create a new A/B test |
| GET | `/` | List A/B tests |
| GET | `/{test_id}` | Get an A/B test |
| POST | `/{test_id}/start` | Start an A/B test |
| POST | `/{test_id}/stop` | Stop an A/B test |
| GET | `/{test_id}/metrics` | Get test metrics |
| POST | `/{test_id}/assign` | Assign a variant |
| DELETE | `/{test_id}` | Delete a draft test |

**Example - Create Test:**
```bash
POST /api/v1/rules/ab-tests/
{
  "test_id": "test_risk_threshold_v2",
  "test_name": "Test new risk threshold",
  "rule_id": "risk_rule_1",
  "ruleset_id": 1,
  "variant_a_version": "1.0",
  "variant_b_version": "2.0",
  "traffic_split_a": 0.5,
  "traffic_split_b": 0.5,
  "duration_hours": 168,
  "min_sample_size": 1000,
  "confidence_level": 0.95
}
```

**Example - Get Metrics:**
```bash
GET /api/v1/rules/ab-tests/test_risk_threshold_v2/metrics
```

**Example - Assign Variant:**
```bash
POST /api/v1/rules/ab-tests/test_risk_threshold_v2/assign
{
  "assignment_key": "user_session_abc123"
}
```

## Integration with Rule Execution

### A/B Testing Integration

The `services/ab_testing_integration.py` module provides utilities to integrate A/B testing into rule execution.

**Key Functions:**

#### `apply_ab_test_to_execution(data, test_id, assignment_key)`
Applies A/B testing to rule execution.

```python
from services.ab_testing_integration import apply_ab_test_to_execution

# Apply A/B testing
ab_context = apply_ab_test_to_execution(
    data=input_data,
    test_id="test_risk_threshold_v2",
    assignment_key="user_session_abc123"
)

# Returns:
# {
#   "ab_test_id": "test_risk_threshold_v2",
#   "ab_test_variant": "A",
#   "ab_test_version": "1.0"
# }
```

#### `get_assignment_key_from_data(data)`
Extracts an assignment key from input data for A/B testing.

**Priority Order:**
1. `user_id` field
2. `session_id` field
3. `correlation_id` field
4. `customer_id` field
5. Generated hash of entire data object

### Rule Execution with A/B Testing

When executing rules with A/B testing:

1. **Input data** contains user/session identifiers
2. **Assignment key** is extracted from data
3. **Variant is assigned** using hash-based routing (consistent for same key)
4. **Rule version** is loaded based on assigned variant
5. **Execution is logged** with A/B test context
6. **Metrics are collected** for statistical analysis

**Example Flow:**
```python
# User request
input_data = {
    "user_id": "user123",
    "income": 50000,
    "age": 30,
    # ... other fields
}

# Apply A/B testing
ab_context = apply_ab_test_to_execution(
    data=input_data,
    test_id="test_risk_threshold_v2"
)

# Execute rules with variant version
result = rules_exec(
    data=input_data,
    # A/B test context is applied internally
)

# Result includes A/B test information
# {
#   "total_points": 50.0,
#   "pattern_result": "YYY",
#   "action_recommendation": "approve",
#   "ab_test_id": "test_risk_threshold_v2",
#   "ab_test_variant": "A",
#   "ab_test_version": "1.0"
# }
```

## Database Migration

To apply the database changes:

```bash
# Using Alembic
alembic upgrade head

# Or using the specific migration
alembic upgrade add_rule_versioning_ab_testing
```

**Migration creates:**
- `rule_versions` table
- `rule_ab_tests` table
- `test_assignments` table
- A/B test columns on `execution_logs` table (`ab_test_id`, `ab_test_variant`)

## Statistical Analysis

The A/B testing engine includes statistical significance testing using chi-square tests.

**Metrics Tracked:**
- Total executions per variant
- Success/failure rates
- Average execution time
- Average total points
- Statistical significance (p-value)

**Significance Threshold:**
- Default confidence level: 95%
- Configurable per test
- Calculated using chi-square test on success/failure rates

## Best Practices

### Rule Versioning

1. **Always provide change reasons** - Helps with auditing and decision-making
2. **Compare before rolling back** - Use comparison endpoint to understand differences
3. **Review version history** - Before making changes, check previous versions
4. **Tag important versions** - Use metadata to mark production releases

### A/B Testing

1. **Start with small samples** - Validate test configuration before full rollout
2. **Set minimum sample sizes** - Ensure statistical power
3. **Monitor test duration** - Don't let tests run too long
4. **Document test hypotheses** - Use descriptions to track what you're testing
5. **Review metrics regularly** - Check for anomalies or issues
6. **Stop tests early if needed** - Don't wait for completion if issues arise

### Assignment Keys

1. **Use stable identifiers** - User IDs are better than session IDs for consistency
2. **Handle new users** - Assign new users to running tests automatically
3. **Consider caching** - Cache variant assignments to reduce database load
4. **Log assignment decisions** - Track which users got which variants

## Security Considerations

1. **Access Control** - Versioning and A/B testing endpoints should require authentication
2. **Audit Trail** - All version changes and test actions are tracked with `created_by` fields
3. **Data Privacy** - Assignment keys should be hashed and not expose sensitive data
4. **Test Isolation** - Tests should not interfere with production rules until explicitly started

## Performance Considerations

1. **Database Indexing** - All queries are indexed for performance
2. **Hash-based Assignment** - O(1) assignment complexity
3. **Caching** - Consider caching test configurations and assignments
4. **Batch Processing** - Use batch endpoints for metrics retrieval

## Troubleshooting

### Common Issues

**Issue:** Test not assigning variants
- **Cause:** Test not in "running" status
- **Solution:** Call `/start` endpoint on the test

**Issue:** Uneven traffic splits
- **Cause:** Assignment keys not uniformly distributed
- **Solution:** Use stable user IDs as assignment keys

**Issue:** Low statistical significance
- **Cause:** Sample size too small
- **Solution:** Increase `min_sample_size` or test duration

**Issue:** Rollback not working
- **Cause:** Version number not found
- **Solution:** Check version history endpoint first

## Future Enhancements

Potential improvements for future versions:

1. **Multi-variant testing** - Support for A/B/n tests
2. **Automated rollback** - Auto-rollback on error rate thresholds
3. **Bayesian analysis** - Alternative to frequentist statistics
4. **Real-time metrics** - WebSocket-based metric updates
5. **Test templates** - Pre-configured test setups
6. **Variant preview** - Preview results before starting tests
7. **Gradual rollout** - Traffic ramp-up for winning variants
