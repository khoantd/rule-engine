# Real-Time Rule Hot Reload

This document describes the Real-Time Rule Hot Reload system for the Rule Engine.

## Overview

The Real-Time Rule Hot Reload system enables rules to be updated and reloaded without restarting the application or service. This provides:

1. **In-Memory Caching**: Fast rule execution using cached rules
2. **Thread-Safe Operations**: Safe concurrent access to rule cache
3. **Automatic Reloading**: Monitor database for changes
4. **Manual Triggering**: API endpoints to trigger reloads on demand
5. **Real-Time Notifications**: WebSocket support for reload events
6. **Health Monitoring**: Track reload status and health

## Architecture

### Components

#### RuleRegistry (`common/rule_registry.py`)
Thread-safe in-memory cache for rules and rulesets.

**Key Features:**
- Thread-safe read/write operations using RLock
- Version tracking for cache invalidation
- Change notifications via subscriber pattern
- Ruleset-level organization
- Rule version history tracking

**Methods:**
- `get_rule(rule_id)` - Get a single rule
- `get_rules(ruleset_id)` - Get all rules or filtered by ruleset
- `add_rule(rule)` - Add or update a rule
- `update_rule(rule)` - Update an existing rule
- `remove_rule(rule_id)` - Remove a rule
- `get_ruleset(ruleset_id)` - Get a ruleset
- `subscribe(callback)` - Subscribe to change notifications
- `get_stats()` - Get registry statistics

#### HotReloadService (`services/hot_reload.py`)
Service for monitoring and reloading rules.

**Key Features:**
- Automatic change detection via polling
- Configurable reload intervals
- Rule validation before reloading
- Graceful error handling
- Reload history tracking
- Health monitoring

**Methods:**
- `start()` - Start automatic monitoring thread
- `stop()` - Stop automatic monitoring thread
- `reload_rules(...)` - Reload rules from database
- `reload_single_rule(rule_id)` - Reload a specific rule
- `reload_ruleset(ruleset_id)` - Reload a ruleset
- `validate_reload()` - Validate current rules
- `get_status()` - Get reload service status
- `get_reload_history()` - Get reload history

#### ReloadNotificationManager (`api/websocket/hot_reload.py`)
Manages WebSocket connections for real-time notifications.

**Key Features:**
- WebSocket connection management
- Broadcast notifications to all clients
- Status updates on connection
- Keep-alive ping/pong support

**Methods:**
- `connect(websocket)` - Accept new WebSocket connection
- `disconnect(websocket)` - Remove WebSocket connection
- `broadcast(event_type, data)` - Broadcast event to all clients
- `send_status(websocket)` - Send current status to client

#### HotReloadIntegration (`services/hot_reload_integration.py`)
Utilities to integrate hot reload into rule execution.

**Key Functions:**
- `get_rules_from_registry()` - Get rules from cache for execution
- `execute_rules_from_registry()` - Execute rules using cached rules
- `validate_registry_rules()` - Validate all cached rules
- `get_registry_info()` - Get registry information
- `is_registry_fresh()` - Check if cache is recent

## API Endpoints

### Hot Reload Endpoints

**Base Path:** `/api/v1/rules/hot-reload`

| Method | Path | Description |
|---------|-------|-------------|
| GET | `/status` | Get hot reload service status |
| POST | `/reload` | Trigger rule reload |
| POST | `/reload/rule/{rule_id}` | Reload a single rule |
| POST | `/reload/ruleset/{ruleset_id}` | Reload a ruleset |
| POST | `/validate` | Validate current rules |
| POST | `/monitoring/start` | Start automatic monitoring |
| POST | `/monitoring/stop` | Stop automatic monitoring |
| GET | `/history` | Get reload history |

**Example - Get Status:**
```bash
GET /api/v1/rules/hot-reload/status
```

Response:
```json
{
  "monitoring_active": true,
  "auto_reload_enabled": true,
  "reload_interval_seconds": 30,
  "validation_enabled": true,
  "last_check_time": "2026-02-01T10:30:00",
  "last_reload_time": "2026-02-01T10:25:00",
  "last_reload_status": "success",
  "reload_count": 5,
  "registry": {
    "rule_count": 10,
    "ruleset_count": 2,
    "version": 5,
    "last_reload": "2026-02-01T10:25:00"
  }
}
```

**Example - Trigger Reload:**
```bash
POST /api/v1/rules/hot-reload/reload
{
  "ruleset_id": 1,
  "rule_id": null,
  "force": true,
  "validate": true
}
```

Response:
```json
{
  "status": "success",
  "timestamp": "2026-02-01T10:30:00",
  "reload_time_ms": 45.5,
  "rules_loaded": 10,
  "rulesets_loaded": 2,
  "reload_count": 6,
  "filtered_by": {
    "ruleset_id": 1,
    "rule_id": null
  }
}
```

### Health Check Endpoints

**Base Path:** `/health`

| Method | Path | Description |
|---------|-------|-------------|
| GET | `/health/hot-reload` | Get hot reload health status |

**Example - Health Check:**
```bash
GET /health/hot-reload
```

Response:
```json
{
  "status": "healthy",
  "monitoring_active": true,
  "auto_reload_enabled": true,
  "last_reload": "2026-02-01T10:25:00",
  "reload_count": 5,
  "last_reload_status": "success",
  "registry": {
    "rule_count": 10,
    "ruleset_count": 2,
    "version": 5,
    "last_reload": "2026-02-01T10:25:00"
  },
  "checks": {
    "monitoring_active": true,
    "registry_has_rules": true,
    "last_reload_successful": true
  }
}
```

### WebSocket Endpoints

| Method | Path | Description |
|---------|-------|-------------|
| WS | `/ws/hot-reload` | WebSocket for real-time reload notifications |

**Example - WebSocket Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/hot-reload');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Event:', message.event_type);
  console.log('Data:', message.data);
};

// Request status
ws.send(JSON.stringify({ type: 'status' }));

// Keep-alive
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

**WebSocket Message Format:**
```json
{
  "event_type": "rules_reloaded",
  "timestamp": "2026-02-01T10:30:00",
  "data": {
    "status": "success",
    "timestamp": "2026-02-01T10:30:00",
    "reload_time_ms": 45.5,
    "rules_loaded": 10,
    "rulesets_loaded": 2
  }
}
```

**Event Types:**
- `rules_reloaded` - Rules have been reloaded
- `rule_added` - A new rule was added to registry
- `rule_updated` - An existing rule was updated
- `rule_removed` - A rule was removed from registry
- `ruleset_added` - A new ruleset was added
- `ruleset_removed` - A ruleset was removed
- `registry_cleared` - Registry was cleared
- `status` - Registry/hot reload status

## Integration with Rule Execution

### Using Cached Rules

To use hot-reloaded rules in execution:

```python
from services.hot_reload_integration import execute_rules_from_registry

# Execute rules from registry (hot-reloaded cache)
result = execute_rules_from_registry(
    data=input_data,
    ruleset_id=1
)

# Result includes registry version
print(f"Total points: {result['total_points']}")
print(f"Registry version: {result['registry_version']}")
```

### Getting Registry Information

```python
from services.hot_reload_integration import get_registry_info, is_registry_fresh

# Get registry information
info = get_registry_info()
print(f"Version: {info['version']}")
print(f"Last reload: {info['last_reload']}")
print(f"Rule count: {info['rule_count']}")

# Check if registry is fresh (reloaded within 5 minutes)
if is_registry_fresh(max_age_seconds=300):
    print("Registry is fresh")
else:
    print("Registry may be stale")
```

### Validating Rules

```python
from services.hot_reload_integration import validate_registry_rules

# Validate all rules in registry
validation = validate_registry_rules()

if validation['valid']:
    print("All rules are valid")
else:
    print(f"Found {validation['invalid_rules']} invalid rules")
    for error in validation['errors']:
        print(f"  Rule {error['rule_id']}: {error['error']}")
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOT_RELOAD_ENABLED` | `true` | Enable automatic hot reload |
| `HOT_RELOAD_INTERVAL_SECONDS` | `30` | Check interval in seconds |
| `HOT_RELOAD_VALIDATION_ENABLED` | `true` | Validate rules before reloading |
| `HOT_RELOAD_MAX_AGE_SECONDS` | `300` | Max age for registry to be considered fresh |

### Startup Configuration

```python
from services.hot_reload import get_hot_reload_service

# Get service instance
hot_reload_service = get_hot_reload_service()

# Start monitoring
hot_reload_service.start()

# Customize if needed
hot_reload_service._auto_reload_enabled = True
hot_reload_service._reload_interval_seconds = 30
hot_reload_service._validation_enabled = True
```

## Monitoring and Metrics

### Metrics Tracked

The hot reload system tracks the following metrics:

- `rule_reloads` - Total number of reloads
- `rule_reload_time` - Time taken for each reload (milliseconds)
- `rules_reloaded` - Number of rules reloaded
- `monitoring_active` - Whether monitoring is active
- `registry_version` - Current registry version

### Health Checks

**Health Status Indicators:**
- `monitoring_active` - Monitoring thread is running
- `registry_has_rules` - Registry contains rules
- `last_reload_successful` - Last reload was successful

**Health Status:**
- `healthy` - All health checks pass
- `unhealthy` - One or more health checks fail

## Best Practices

### 1. Rule Updates

✅ **Use API endpoints** for rule updates instead of direct database changes
✅ **Validate rules** before reloading to prevent issues
✅ **Check health** after reloads to ensure success
✅ **Monitor WebSocket notifications** for real-time updates
✅ **Use appropriate reload scope** - reload only what needs reloading

### 2. Reload Frequency

✅ **Balance frequency** - Too frequent = unnecessary load, too infrequent = stale rules
✅ **Consider traffic patterns** - Reload during low-traffic periods
✅ **Use manual triggers** for critical updates
✅ **Monitor reload time** - Keep reloads fast (< 1 second recommended)

### 3. Monitoring

✅ **Set up alerts** for failed reloads
✅ **Monitor registry freshness** - Ensure rules aren't stale
✅ **Track reload metrics** - Identify performance issues
✅ **Review health checks** - Regularly check service health

### 4. Validation

✅ **Always validate** - Prevent invalid rules from entering production
✅ **Review validation errors** - Fix issues before reloading
✅ **Test in staging** - Validate rules in non-production environment
✅ **Use validation endpoints** - Check before deploying

## Troubleshooting

### Common Issues

**Issue:** Rules not reloading automatically

**Solutions:**
1. Check if monitoring is active: `GET /api/v1/rules/hot-reload/status`
2. Verify `HOT_RELOAD_ENABLED=true` in environment
3. Check database connection
4. Review logs for monitoring errors

**Issue:** Reloads taking too long

**Solutions:**
1. Reduce number of rules to reload at once
2. Increase `HOT_RELOAD_INTERVAL_SECONDS` to reduce frequency
3. Optimize database queries
4. Consider caching ruleset queries

**Issue:** Invalid rules in cache

**Solutions:**
1. Validate rules before reloading: `POST /api/v1/rules/hot-reload/validate`
2. Fix validation errors in database
3. Manually trigger reload after fixes
4. Check rule validation logic

**Issue:** WebSocket connection dropping

**Solutions:**
1. Implement keep-alive with ping/pong
2. Check network connectivity
3. Verify WebSocket endpoint URL
4. Review firewall rules

**Issue:** Stale rules in execution

**Solutions:**
1. Check registry freshness: `GET /health/hot-reload`
2. Trigger manual reload if needed
3. Verify monitoring is working
4. Check database update timestamps

## Performance Considerations

### 1. Thread Safety

- All registry operations use `threading.RLock()` for thread safety
- Multiple readers can access rules simultaneously
- Writers have exclusive access during updates

### 2. Memory Usage

- Cached rules consume memory proportional to rule count
- For large rule sets (> 10,000 rules), consider:
  - Partitioning by ruleset
  - LRU cache with size limits
  - Periodic cache clearing

### 3. Reload Latency

- Target reload time: < 1000ms for 1000 rules
- Factors affecting reload time:
  - Database query performance
  - Rule validation time
  - Number of rules to reload
  - Network latency (if remote database)

### 4. Monitoring Overhead

- Monitoring thread checks database every interval
- Each check is a simple query (count rule IDs)
- Minimal overhead at 30-second intervals
- Adjust interval based on needs

## Security Considerations

1. **Access Control** - Hot reload endpoints should require authentication
2. **Audit Trail** - All reloads are logged with timestamps
3. **Validation** - Rules are validated before entering cache
4. **Rate Limiting** - Consider rate limiting manual reload endpoints
5. **WebSocket Authentication** - Implement WebSocket authentication if needed

## Future Enhancements

Potential improvements for future versions:

1. **Database Triggers** - Use PostgreSQL NOTIFY for instant change detection
2. **Incremental Reloads** - Reload only changed rules, not entire rulesets
3. **Cache Partitioning** - Partition cache by ruleset for better performance
4. **Rollback Support** - Quick rollback to previous cache state
5. **Metrics Dashboard** - Real-time dashboard for reload metrics
6. **Multi-Instance Sync** - Sync cache across multiple service instances
7. **Rule Dependency Tracking** - Track dependencies and reload in correct order
8. **Cache Warming** - Pre-load frequently used rulesets on startup

## Example Workflows

### Workflow 1: Deploy New Rules

1. Create/update rules in database via management API
2. Validate rules: `POST /api/v1/rules/hot-reload/validate`
3. Trigger reload: `POST /api/v1/rules/hot-reload/reload`
4. Monitor WebSocket for reload notification
5. Verify health: `GET /health/hot-reload`
6. Test rule execution with new rules

### Workflow 2: Monitoring Dashboard

1. Connect WebSocket: `ws://localhost:8000/ws/hot-reload`
2. Subscribe to events
3. Display reload notifications
4. Show registry statistics
5. Alert on failed reloads or stale rules

### Workflow 3: Staging to Production

1. Update rules in staging environment
2. Validate rules: `POST /api/v1/rules/hot-reload/validate`
3. Test rule execution with new rules
4. Monitor metrics for issues
5. Promote to production
6. Trigger production reload
7. Monitor production WebSocket for successful reload

## Glossary

- **Registry**: In-memory cache of rules and rulesets
- **Hot Reload**: Reloading rules without restarting the service
- **Monitoring Thread**: Background thread that checks for rule changes
- **Registry Version**: Incremental version number that changes on each reload
- **Subscriber**: Function registered to receive change notifications
- **WebSocket**: Bidirectional communication protocol for real-time updates
- **Health Check**: Endpoint to verify service health status
- **Freshness**: Whether registry has been recently reloaded
