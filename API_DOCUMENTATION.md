# Rule Engine API Documentation

Comprehensive REST API reference for the Rule Engine service — covering rule execution, management, versioning, A/B testing, hot reload, and workflow orchestration.

> **For AI Agents**: This document is structured for both human readers and AI agents. Each section includes the endpoint signature, all request/response fields with types and constraints, and concrete `curl` examples. Start with the [Architecture Overview](#architecture-overview) to understand how the system works, then consult individual endpoint sections.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Base URL & Versioning](#base-url--versioning)
- [Authentication](#authentication)
- [Common Patterns](#common-patterns)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Health & Status](#health--status)
  - [Rule Execution](#rule-execution)
  - [Batch Rule Execution](#batch-rule-execution)
  - [DMN Rule Execution](#dmn-rule-execution)
  - [Rule Management](#rule-management)
  - [Condition Management](#condition-management)
  - [Attribute Management](#attribute-management)
  - [Action Management](#action-management)
  - [Ruleset Management](#ruleset-management)
  - [Workflow Execution](#workflow-execution)
  - [Workflow Management](#workflow-management)
  - [Rule Versioning](#rule-versioning)
  - [A/B Testing](#ab-testing)
  - [Hot Reload](#hot-reload)
  - [Consumer Management](#consumer-management)
  - [Execution History](#execution-history)
  - [WebSocket](#websocket)
- [Data Models Reference](#data-models-reference)
- [Configuration Reference](#configuration-reference)
- [Best Practices](#best-practices)

---

## Architecture Overview

The Rule Engine evaluates a set of business rules against arbitrary input data and returns a scored recommendation.

### Core Concepts

| Concept | Description |
|--------|-------------|
| **Attribute** | A named field that can appear in input data (e.g., `issue`, `publisher`). Defines the data type expected. |
| **Condition** | A single predicate: `attribute` + `equation` + `constant` (e.g., `issue greater_than 30`). |
| **Rule** | Wraps one or more conditions. Has a `priority`, a `weight`, a `rule_point` value, and an `action_result` string (e.g., `"Y"` or `"N"`). |
| **Pattern** | Concatenated `action_result` values from all rules in evaluation order (e.g., `"YYN"`). |
| **Action** | Maps a pattern string to a human-readable recommendation (e.g., `"YYY"` → `"Approved"`). |
| **Ruleset** | A named collection of rules + their corresponding action mappings. |
| **Workflow** | An ordered list of named stages. Each stage is handled by a domain handler via the Chain of Responsibility pattern. |

### Execution Flow

```
Input Data (Dict)
    │
    ▼
Load Rules from Registry / Database / File / S3
    │
    ▼
For each Rule (ordered by priority):
  - Evaluate Condition against Input Data
  - If matched → collect action_result ("Y"), add rule_point × weight
  - If not matched → collect action_result ("N" or "-")
    │
    ▼
Build Pattern Result (concatenate action_results)
    │
    ▼
Lookup Action by Pattern → action_recommendation
    │
    ▼
Return: { total_points, pattern_result, action_recommendation }
```

### Storage Options

| Source | Config Variable | Description |
|--------|-----------------|-------------|
| JSON files | `RULES_CONFIG_PATH` | Default; loads from local JSON files |
| PostgreSQL / TimescaleDB | `USE_DATABASE=true`, `DATABASE_URL` | Full CRUD via management endpoints |
| AWS S3 | `S3_BUCKET` | Config stored in S3; useful for cloud deployments |

Rules are cached in an **in-memory registry** (`RuleRegistry`) at startup. The Hot Reload API allows refreshing the registry without restarting the server.

---

## Base URL & Versioning

```
http://localhost:8000
```

All resource endpoints are under `/api/v1`. Health and root endpoints are at the top level.

| Prefix | Usage |
|--------|-------|
| `/` | Root info |
| `/health` | Health checks |
| `/api/v1/rules/` | Rule execution, versioning, A/B testing, hot reload |
| `/api/v1/management/` | CRUD for rules, conditions, attributes, actions, rulesets |
| `/api/v1/workflow/` | Workflow execution |
| `/api/v1/workflows` | Workflow definitions CRUD |
| `/api/v1/dmn/` | DMN file upload and parsing |
| `/api/v1/executions` | Execution history queries |
| `/consumers` | Consumer management |

Interactive docs (Swagger UI) are available at `http://localhost:8000/docs` when the server is running.

---

## Authentication

API key authentication is **disabled by default**. Enable it via environment variables.

### Enable

```bash
export API_KEY_ENABLED=true
export API_KEY=your-secret-api-key
```

### Usage

Include the key in the `X-API-Key` request header:

```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:8000/api/v1/rules/execute ...
```

### Bypass Paths

The following paths bypass authentication regardless of configuration:
- `GET /` — root info
- `GET /health` — health check
- `GET /docs`, `GET /redoc`, `GET /openapi.json` — API documentation

### Error Responses

| Scenario | HTTP Status |
|---------|-------------|
| API key required but missing | `401 Unauthorized` |
| API key provided but invalid | `403 Forbidden` |

---

## Common Patterns

### Correlation IDs

Every request can carry a `correlation_id` for end-to-end tracing. If omitted, the server generates one automatically.

- Sent in request body as `correlation_id` field, or
- Sent in request header as `X-Correlation-ID`
- Always returned in response body and `X-Correlation-ID` header
- Always included in server logs

### Dry Run Mode

Most execution endpoints support `"dry_run": true`. In dry-run mode:
- Rules are evaluated but **no side effects occur**
- The response includes detailed per-rule evaluation results (`rule_evaluations`, `would_match`, `would_not_match`)
- Useful for debugging rule configurations and testing new rules before deployment

### Pagination

List endpoints accept `offset` and `limit` query parameters where supported.

---

## Error Handling

All errors return a consistent JSON body:

```json
{
  "error_type": "DataValidationError",
  "message": "Input data must be a dictionary",
  "error_code": "DATA_INVALID_TYPE",
  "context": {
    "data_type": "str",
    "expected_type": "dict"
  },
  "correlation_id": "req-12345"
}
```

### HTTP Status Codes

| Code | Meaning | Cause |
|------|---------|-------|
| `200` | OK | Success |
| `204` | No Content | Successful deletion |
| `400` | Bad Request | Input validation failed |
| `401` | Unauthorized | Authentication required |
| `403` | Forbidden | Invalid API key |
| `404` | Not Found | Resource does not exist |
| `409` | Conflict | Duplicate resource |
| `422` | Unprocessable Entity | Schema validation error |
| `500` | Internal Server Error | Unexpected server-side failure |

### Error Types

| `error_type` | HTTP | Description |
|-------------|------|-------------|
| `DataValidationError` | 400/404/409 | Invalid input or missing/duplicate resource |
| `ConfigurationError` | 500 | Rule config not found or malformed |
| `RuleEvaluationError` | 500 | Failure during rule condition evaluation |
| `WorkflowError` | 500 | Workflow handler not found or stage failure |
| `SecurityError` | 403 | Authentication/authorization failure |
| `NotFoundError` | 404 | Resource not found |

---

## Endpoints

---

### Health & Status

#### `GET /`

Returns basic API info.

**Response `200`**
```json
{
  "name": "Rule Engine API",
  "version": "1.0.0",
  "description": "REST API for Rule Engine service",
  "docs_url": "/docs",
  "health_url": "/health"
}
```

---

#### `GET /health`

Returns service health status. Does not require authentication.

**Response `200`**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "uptime_seconds": 3600.5,
  "environment": "production"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes | `"healthy"` or `"unhealthy"` |
| `version` | string | Yes | API version |
| `timestamp` | datetime (ISO 8601) | Yes | Current UTC time |
| `uptime_seconds` | float | No | Seconds since server start |
| `environment` | string | No | `dev` / `staging` / `production` |

---

#### `GET /health/hot-reload`

Returns health status of the hot reload service.

**Response `200`** — Dict with hot reload service status details.

---

### Rule Execution

#### `POST /api/v1/rules/execute`

Evaluates all loaded rules against a single input data item.

**Request Body**

```json
{
  "data": {
    "issue": 35,
    "title": "Superman",
    "publisher": "DC"
  },
  "dry_run": false,
  "correlation_id": "req-12345",
  "consumer_id": "client-abc"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data` | object | Yes | Input data dictionary. Keys should match configured attribute names. |
| `dry_run` | boolean | No | Default `false`. If `true`, returns detailed per-rule evaluations without side effects. |
| `correlation_id` | string | No | Tracing ID. Auto-generated if omitted. |
| `consumer_id` | string | No | Identifies the calling client for usage tracking. |

**Response `200`** (normal mode)

```json
{
  "total_points": 1050.0,
  "pattern_result": "YYY",
  "action_recommendation": "Approved",
  "decision_outputs": null,
  "rule_evaluations": null,
  "would_match": null,
  "would_not_match": null,
  "dry_run": false,
  "execution_time_ms": 45.2,
  "correlation_id": "req-12345"
}
```

**Response `200`** (normal mode, no rules matched — optional fields often `null`)

```json
{
  "total_points": 0.0,
  "pattern_result": "-",
  "action_recommendation": null,
  "decision_outputs": null,
  "rule_evaluations": null,
  "would_match": null,
  "would_not_match": null,
  "dry_run": false,
  "execution_time_ms": 951.29,
  "correlation_id": "req-12345"
}
```

**Response `200`** (dry run mode)

```json
{
  "total_points": 1050.0,
  "pattern_result": "YYY",
  "action_recommendation": "Approved",
  "rule_evaluations": [
    {
      "rule_name": "Rule 1",
      "rule_priority": 1,
      "condition": "issue greater_than 30",
      "matched": true,
      "action_result": "Y",
      "rule_point": 20.0,
      "weight": 30.0,
      "execution_time_ms": 2.5
    }
  ],
  "would_match": [...],
  "would_not_match": [...],
  "dry_run": true,
  "execution_time_ms": 45.2,
  "correlation_id": "req-12345"
}
```

| Field | Type | In dry_run only | Description |
|-------|------|-----------------|-------------|
| `total_points` | float | No | Sum of `rule_point × weight` for all matched rules |
| `pattern_result` | string | No | Concatenated `action_result` values (e.g. `"YYN"`); `"-"` when no rule matched (per non-match token) |
| `action_recommendation` | string or null | No | Recommendation when `pattern_result` matches an actions-config key exactly; otherwise `null` |
| `rule_evaluations` | array or null | Yes | All rules evaluated with details; `null` when `dry_run` is `false` |
| `would_match` | array or null | Yes | Rules that matched; `null` when `dry_run` is `false` |
| `would_not_match` | array or null | Yes | Rules that did not match; `null` when `dry_run` is `false` |
| `decision_outputs` | object | No | DMN outputs; `null` for JSON `/rules/execute` (use `/rules/execute-dmn` for populated values) |
| `execution_time_ms` | float | No | Total execution time |
| `correlation_id` | string | No | Tracing ID |

#### When response fields are `null`

Responses use optional JSON members that may be `null` when they do not apply:

| Field | Why `null` |
|-------|------------|
| `rule_evaluations`, `would_match`, `would_not_match` | Populated only when **`dry_run` is `true`**. In normal mode the API omits detailed evaluation lists and these fields serialize as `null`. |
| `decision_outputs` | Set by **DMN** execution paths. **`POST /api/v1/rules/execute`** (JSON rulesets) does not fill this; use **`POST /api/v1/rules/execute-dmn`** (or upload variant) for decision outputs. |
| `action_recommendation` | Set only when **`pattern_result`** matches a key **exactly** in the actions configuration. Also `null` if actions config is empty, invalid, or failed to load (see server logs). |

**Interpreting a sparse result:** `total_points` of `0.0` with `pattern_result` of `"-"` usually means **no rules matched**—non-matching rules contribute `"-"` to the concatenated pattern, and a single evaluated rule yields exactly `"-"`. Unless your actions map defines a pattern key `"-"`, **`action_recommendation` will be `null`**.

> **Note:** Absent vs `null` for optional fields is normal; clients should treat `null` as “not applicable,” not an error. If you need per-rule detail without changing rules, re-run with **`dry_run: true`**.

**`curl` example**

```bash
curl -X POST http://localhost:8000/api/v1/rules/execute \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"issue": 35, "title": "Superman", "publisher": "DC"},
    "dry_run": false
  }'
```

---

#### `POST /api/v1/rules/{ruleset_name}/execute`

Evaluates rules from a specific named ruleset against a single input item. The consumer identified by `consumer_id` must have an active registration for the target ruleset (see [Consumer Management](#consumer-management)).

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ruleset_name` | string | Name of the ruleset to execute |

**Request Body** — Same schema as `POST /api/v1/rules/execute`.

```json
{
  "data": {
    "issue": 35,
    "publisher": "DC"
  },
  "dry_run": false,
  "correlation_id": "req-12345",
  "consumer_id": "client-abc"
}
```

**Response `200`** — Same `RuleExecutionResponse` schema as `POST /api/v1/rules/execute`.

**Response `403`** — Consumer is not registered for the ruleset.

**Response `404`** — Ruleset not found.

**Example**

```bash
curl -X POST http://localhost:8000/api/v1/rules/comic-scoring/execute \
  -H "Content-Type: application/json" \
  -d '{"data": {"issue": 35, "publisher": "DC"}, "consumer_id": "client-abc"}'
```

---

### Batch Rule Execution

#### `POST /api/v1/rules/batch`

Evaluates rules against a list of input items, optionally in parallel.

**Request Body**

```json
{
  "data_list": [
    {"issue": 35, "title": "Superman", "publisher": "DC"},
    {"issue": 10, "title": "Batman", "publisher": "DC"}
  ],
  "dry_run": false,
  "max_workers": 4,
  "correlation_id": "batch-12345",
  "consumer_id": "client-abc"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data_list` | array of objects | Yes | Must have at least 1 item. Each item is evaluated independently. |
| `dry_run` | boolean | No | Default `false`. |
| `max_workers` | integer | No | Number of parallel workers. Must be positive. Auto-determined if omitted. |
| `correlation_id` | string | No | Batch tracing ID. |
| `consumer_id` | string | No | Calling client identifier. |

**Response `200`**

```json
{
  "batch_id": "batch-12345",
  "results": [
    {
      "item_index": 0,
      "correlation_id": "batch-12345-0",
      "status": "success",
      "total_points": 1050.0,
      "pattern_result": "YYY",
      "action_recommendation": "Approved"
    },
    {
      "item_index": 1,
      "correlation_id": "batch-12345-1",
      "status": "failed",
      "error": "Condition evaluation failed",
      "error_type": "RuleEvaluationError"
    }
  ],
  "summary": {
    "total_executions": 2,
    "successful_executions": 1,
    "failed_executions": 1,
    "total_execution_time_ms": 89.5,
    "avg_execution_time_ms": 44.75,
    "success_rate": 50.0
  },
  "dry_run": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `batch_id` | string | Unique batch ID |
| `results` | array | One entry per input item, in the same order as `data_list` |
| `results[].item_index` | integer | Zero-based index into `data_list` |
| `results[].status` | string | `"success"` or `"failed"` |
| `results[].error` | string | Present only on failure |
| `summary.success_rate` | float | Percentage 0–100 |

> Failures in individual items do not abort the batch; they are captured and reported in the result.

**`curl` example**

```bash
curl -X POST http://localhost:8000/api/v1/rules/batch \
  -H "Content-Type: application/json" \
  -d '{
    "data_list": [
      {"issue": 35, "title": "Superman"},
      {"issue": 10, "title": "Batman"}
    ],
    "max_workers": 4
  }'
```

---

### DMN Rule Execution

DMN (Decision Model Notation) endpoints allow executing rules defined in an external DMN XML file rather than the server's configured ruleset.

#### `POST /api/v1/rules/execute-dmn`

Execute rules from an inline DMN definition.

**Request Body**

```json
{
  "dmn_content": "<definitions>...</definitions>",
  "data": {"issue": 35, "publisher": "DC"},
  "dry_run": false,
  "correlation_id": "dmn-req-001"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dmn_file` | string | No* | Path to a DMN file on the server filesystem |
| `dmn_content` | string | No* | Raw DMN XML string |
| `data` | object | Yes | Input data |
| `dry_run` | boolean | No | Default `false` |
| `correlation_id` | string | No | Tracing ID |

*Either `dmn_file` or `dmn_content` must be provided.

**Response `200`** — Same shape as `RuleExecutionResponse` (see [Rule Execution](#rule-execution)). Unlike JSON `/rules/execute`, DMN responses may include **`decision_outputs`** when decisions produce mapped outputs. For when fields are `null` or omitted, see **When response fields are `null`** under Rule Execution above.

---

#### `POST /api/v1/rules/execute-dmn-upload`

Upload and immediately execute a DMN file (multipart form).

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | DMN XML file |
| `data` | string (JSON) | Yes | Input data as JSON string |
| `dry_run` | boolean | No | Default `false` |
| `consumer_id` | string | No | Calling client identifier |

**Response `200`** — Same shape as `RuleExecutionResponse`.

---

#### `POST /api/v1/dmn/upload`

Upload a DMN file for parsing without executing it immediately.

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | DMN XML file |

**Response `200`**

```json
{
  "filename": "rules.dmn",
  "file_path": "/tmp/uploads/rules.dmn",
  "rules": [...],
  "patterns": [...],
  "rules_count": 5,
  "correlation_id": "upload-abc123"
}
```

---

### Rule Management

Full CRUD for individual rules. Requires the server to be configured with database storage (`USE_DATABASE=true`) or a writable file-based backend.

#### `GET /api/v1/management/rules`

List all rules.

**Response `200`**

```json
{
  "rules": [
    {
      "id": "rule-001",
      "rule_name": "High Issue Number",
      "type": "simple",
      "conditions": ["cond-001"],
      "description": "Checks if issue number is high",
      "result": "Y",
      "weight": 30.0,
      "rule_point": 20.0,
      "priority": 1,
      "action_result": "Y"
    }
  ],
  "count": 1
}
```

---

#### `GET /api/v1/management/rules/{rule_id}`

Get a single rule by ID.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | string | Rule ID |

**Response `200`** — Single `RuleResponse` object.

**Response `404`** — Rule not found.

---

#### `POST /api/v1/management/rules`

Create a new rule.

**Request Body**

```json
{
  "id": "rule-001",
  "rule_name": "High Issue Number",
  "type": "simple",
  "conditions": ["cond-001"],
  "description": "Checks if issue number is high",
  "result": "Y",
  "weight": 30.0,
  "rule_point": 20.0,
  "priority": 1,
  "action_result": "Y"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique rule identifier |
| `rule_name` | string | Yes | Human-readable name |
| `type` | string | No | `"simple"` or `"complex"`. Default `"simple"` |
| `conditions` | array of strings | Yes | Condition IDs to evaluate |
| `description` | string | No | Human-readable description |
| `result` | string | No | Default result |
| `weight` | float | No | Weight multiplier for scoring |
| `rule_point` | float | No | Base points for this rule |
| `priority` | integer | No | Evaluation order (lower = higher priority) |
| `action_result` | string | No | Result token appended to pattern (e.g., `"Y"`) |

**Response `200`** — Created `RuleResponse`.

**Response `409`** — Rule with that ID already exists.

---

#### `PUT /api/v1/management/rules/{rule_id}`

Update an existing rule. All fields are optional; only provided fields are updated.

**Response `200`** — Updated `RuleResponse`.

**Response `404`** — Rule not found.

---

#### `DELETE /api/v1/management/rules/{rule_id}`

Delete a rule by ID.

**Response `204`** — Deleted successfully.

**Response `404`** — Rule not found.

---

### Condition Management

Conditions define a single predicate: `attribute` `equation` `constant`.

#### `GET /api/v1/management/conditions`

List all conditions.

**Response `200`**

```json
{
  "conditions": [
    {
      "condition_id": "cond-001",
      "condition_name": "Issue Greater Than 30",
      "attribute": "issue",
      "equation": "greater_than",
      "constant": 30
    }
  ],
  "count": 1
}
```

---

#### `GET /api/v1/management/conditions/{condition_id}`

Get a single condition.

**Response `200`** — Single `ConditionResponse`.

**Response `404`** — Condition not found.

---

#### `POST /api/v1/management/conditions`

Create a new condition.

**Request Body**

```json
{
  "condition_id": "cond-001",
  "condition_name": "Issue Greater Than 30",
  "attribute": "issue",
  "equation": "greater_than",
  "constant": 30
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `condition_id` | string | Yes | Unique ID |
| `condition_name` | string | Yes | Human-readable name |
| `attribute` | string | Yes | Attribute name to evaluate |
| `equation` | string | Yes | Comparison operator (see below) |
| `constant` | any | Yes | Value to compare against |

**Supported `equation` values**

| Value | Meaning |
|-------|---------|
| `equals` | `attribute == constant` |
| `not_equals` | `attribute != constant` |
| `greater_than` | `attribute > constant` |
| `less_than` | `attribute < constant` |
| `greater_than_or_equal` | `attribute >= constant` |
| `less_than_or_equal` | `attribute <= constant` |
| `contains` | `constant in attribute` |
| `not_contains` | `constant not in attribute` |
| `starts_with` | `attribute.startswith(constant)` |
| `ends_with` | `attribute.endswith(constant)` |
| `in` | `attribute in [constant values]` |
| `not_in` | `attribute not in [constant values]` |

**Response `200`** — Created `ConditionResponse`.

---

#### `PUT /api/v1/management/conditions/{condition_id}`

Update a condition. All fields optional.

**Response `200`** — Updated `ConditionResponse`.

---

#### `DELETE /api/v1/management/conditions/{condition_id}`

**Response `204`**

---

### Attribute Management

Attributes are the named data fields that conditions reference. They define the expected data type.

#### `GET /api/v1/management/attributes`

**Response `200`**

```json
{
  "attributes": [
    {
      "attribute_id": "attr-001",
      "name": "issue",
      "data_type": "integer",
      "description": "Comic issue number",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### `GET /api/v1/management/attributes/{attribute_id}`

**Response `200`** — Single `AttributeResponse`.

---

#### `POST /api/v1/management/attributes`

**Request Body**

```json
{
  "attribute_id": "attr-001",
  "name": "issue",
  "data_type": "integer",
  "description": "Comic issue number"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `attribute_id` | string | Yes | Unique ID |
| `name` | string | Yes | Attribute field name (matches input data keys) |
| `data_type` | string | Yes | `"string"`, `"integer"`, `"float"`, `"boolean"` |
| `description` | string | No | Human-readable description |

**Response `200`** — Created `AttributeResponse`.

---

#### `PUT /api/v1/management/attributes/{attribute_id}`

**Response `200`** — Updated `AttributeResponse`.

---

#### `DELETE /api/v1/management/attributes/{attribute_id}`

**Response `204`**

---

### Action Management

Actions map a pattern string to a recommendation message.

#### `GET /api/v1/management/actions`

**Response `200`**

```json
{
  "actions": {
    "YYY": "Approved",
    "YYN": "Pending Review",
    "YNN": "Rejected"
  },
  "count": 3,
  "items": [
    {"id": "act-001", "pattern": "YYY", "message": "Approved", "ruleset_id": "ruleset-1"}
  ]
}
```

---

#### `GET /api/v1/management/actions/{pattern}`

Get an action by its pattern string.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `pattern` | string | Pattern string (e.g., `YYY`) |

**Response `200`** — Single `ActionResponse`.

---

#### `POST /api/v1/management/actions`

**Request Body**

```json
{
  "pattern": "YYY",
  "message": "Approved",
  "ruleset_id": "ruleset-1"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | string | Yes | Pattern to match (e.g., `"YYN"`) |
| `message` | string | Yes | Recommendation message |
| `ruleset_id` | string | No | Ruleset this action belongs to |

**Response `200`** — Created `ActionResponse`.

---

#### `PUT /api/v1/management/actions/{pattern}`

**Response `200`** — Updated `ActionResponse`.

---

#### `DELETE /api/v1/management/actions/{pattern}`

**Response `204`**

---

### Ruleset Management

A ruleset groups a set of rules with their corresponding action mappings.

#### `GET /api/v1/management/rulesets`

**Response `200`**

```json
{
  "rulesets": [
    {
      "ruleset_name": "comic-scoring",
      "rules": ["rule-001", "rule-002", "rule-003"],
      "actionset": [
        {"pattern": "YYY", "message": "Approved"},
        {"pattern": "YYN", "message": "Pending Review"}
      ]
    }
  ],
  "count": 1
}
```

---

#### `GET /api/v1/management/rulesets/{ruleset_name}`

**Response `200`** — Single `RuleSetResponse`.

---

#### `POST /api/v1/management/rulesets`

**Request Body**

```json
{
  "ruleset_name": "comic-scoring",
  "rules": ["rule-001", "rule-002", "rule-003"],
  "actionset": [
    {"pattern": "YYY", "message": "Approved"},
    {"pattern": "YYN", "message": "Pending Review"},
    {"pattern": "YNN", "message": "Rejected"}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ruleset_name` | string | Yes | Unique ruleset name |
| `rules` | array of strings | Yes | Ordered list of rule IDs |
| `actionset` | array of objects | No | Pattern → message mappings |

**Response `200`** — Created `RuleSetResponse`.

---

#### `PUT /api/v1/management/rulesets/{ruleset_name}`

**Response `200`** — Updated `RuleSetResponse`.

---

#### `DELETE /api/v1/management/rulesets/{ruleset_name}`

**Response `204`**

---

### Workflow Execution

Workflows execute input data through an ordered chain of named stage handlers.

#### `POST /api/v1/workflow/execute`

Execute a workflow with an inline stage definition.

**Request Body**

```json
{
  "process_name": "ticket_processing",
  "stages": ["NEW", "INPROGESS", "FINISHED"],
  "data": {
    "ticket_id": "TICK-123",
    "priority": "high"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `process_name` | string | Yes | Workflow/process identifier |
| `stages` | array of strings | No | Stage names in execution order. Default: `["NEW", "INPROGESS", "FINISHED"]` |
| `data` | object | No | Input data. Default: `{}` |

**Built-in stage handlers**

| Stage Name | Handler | Description |
|-----------|---------|-------------|
| `NEW` | `NewCaseHandler` | Initializes a new case |
| `INPROGESS` | `InProcessCaseHandler` | Processes an in-progress case |
| `FINISHED` | `FinishedCaseHandler` | Finalizes a completed case |

**Response `200`**

```json
{
  "process_name": "ticket_processing",
  "stages": ["NEW", "INPROGESS", "FINISHED"],
  "result": {
    "status": "completed",
    "data": {"ticket_id": "TICK-123", "state": "FINISHED"}
  },
  "execution_time_ms": 123.5
}
```

---

#### `POST /api/v1/workflow/execute-by-name`

Execute a saved workflow definition by name.

**Request Body**

```json
{
  "workflow_name": "comic-review-process",
  "data": {"issue": 35, "title": "Superman"}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workflow_name` | string | Yes | Name of a previously created workflow |
| `data` | object | No | Input data |

**Response `200`** — Same shape as `WorkflowExecutionResponse`.

---

### Workflow Management

CRUD operations for persisted workflow definitions.

#### `POST /api/v1/workflows`

Create a workflow definition.

**Request Body**

```json
{
  "name": "comic-review-process",
  "description": "Workflow for reviewing comic submissions",
  "stages": ["NEW", "INPROGESS", "FINISHED"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique workflow name |
| `description` | string | No | Human-readable description |
| `stages` | array of strings | Yes | Stage names in order |

**Response `200`**

```json
{
  "name": "comic-review-process",
  "description": "Workflow for reviewing comic submissions",
  "is_active": true,
  "stages": [
    {"name": "NEW", "position": 1},
    {"name": "INPROGESS", "position": 2},
    {"name": "FINISHED", "position": 3}
  ],
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

---

#### `GET /api/v1/workflows`

List all workflows.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `is_active` | boolean | Filter by active status |
| `offset` | integer | Pagination offset |
| `limit` | integer | Pagination limit |

**Response `200`** — `{ "workflows": [...], "count": N }`

---

#### `GET /api/v1/workflows/{name}`

Get a workflow by name.

**Response `200`** — Single `WorkflowResponse`.

---

#### `PUT /api/v1/workflows/{name}`

Update a workflow. All fields optional.

**Request Body fields**: `description`, `stages`, `is_active`

**Response `200`** — Updated `WorkflowResponse`.

---

#### `DELETE /api/v1/workflows/{name}`

Delete a workflow. Default is a soft delete.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hard` | boolean | `false` | If `true`, permanently deletes the workflow |

**Response `204`**

---

### Rule Versioning

Every rule change is tracked in a version history. You can compare versions and roll back.

#### `GET /api/v1/rules/versions/{rule_id}`

Get version history for a rule.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | string | Rule ID |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Max versions to return |

**Response `200`** — Array of version objects with change metadata.

---

#### `GET /api/v1/rules/versions/{rule_id}/current`

Get the current (latest) version of a rule.

**Response `200`** — Version object or `null` if no versions exist.

---

#### `GET /api/v1/rules/versions/{rule_id}/{version_number}`

Get a specific version of a rule.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | string | Rule ID |
| `version_number` | integer | Version number |

**Response `200`** — Version object or `null` if not found.

---

#### `POST /api/v1/rules/versions/{rule_id}/compare`

Compare two versions of a rule.

**Request Body**

```json
{
  "version_a": 1,
  "version_b": 3
}
```

**Response `200`** — Dict containing field-level differences between the two versions.

---

#### `POST /api/v1/rules/versions/{rule_id}/rollback`

Roll back a rule to a previous version.

**Request Body**

```json
{
  "version_number": 2,
  "change_reason": "Reverted due to regression in scoring"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version_number` | integer | Yes | Version to restore |
| `change_reason` | string | No | Reason for rollback (stored in version history) |

**Response `200`** — Dict with rollback confirmation and new current version.

---

### A/B Testing

Test two variants of a rule against live traffic before fully committing to a change.

#### `POST /api/v1/rules/ab-tests/`

Create an A/B test.

**Request Body**

```json
{
  "test_id": "ab-test-001",
  "test_name": "High Issue Threshold Test",
  "rule_id": "rule-001",
  "ruleset_id": "comic-scoring",
  "variant_a_version": 1,
  "variant_b_version": 2,
  "traffic_split_a": 50,
  "traffic_split_b": 50,
  "confidence_level": 0.95
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `test_id` | string | Yes | Unique test identifier |
| `test_name` | string | Yes | Human-readable name |
| `rule_id` | string | No* | Rule being tested |
| `ruleset_id` | string | No* | Ruleset being tested |
| `variant_a_version` | integer | Yes | Version number for variant A |
| `variant_b_version` | integer | Yes | Version number for variant B |
| `traffic_split_a` | float | Yes | % of traffic for A (0–100) |
| `traffic_split_b` | float | Yes | % of traffic for B (0–100) |
| `confidence_level` | float | No | Statistical confidence threshold (default 0.95) |

*At least one of `rule_id` or `ruleset_id` is required.

**Response `200`** — Dict with test details and initial status.

---

#### `GET /api/v1/rules/ab-tests/`

List A/B tests.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | string | Filter by rule |
| `status` | string | Filter by status (`active`, `stopped`, `pending`) |
| `limit` | integer | Max results |

**Response `200`** — Array of test objects.

---

#### `GET /api/v1/rules/ab-tests/{test_id}`

Get a single A/B test.

**Response `200`** — Test object or `null` if not found.

---

#### `POST /api/v1/rules/ab-tests/{test_id}/start`

Start an A/B test (begin routing traffic to variants).

**Response `200`** — Updated test status.

---

#### `POST /api/v1/rules/ab-tests/{test_id}/stop`

Stop an A/B test.

**Response `200`** — Updated test status.

---

#### `GET /api/v1/rules/ab-tests/{test_id}/metrics`

Get performance metrics for a running or completed A/B test.

**Response `200`** — Dict containing per-variant metrics (execution counts, average points, etc.).

---

#### `POST /api/v1/rules/ab-tests/{test_id}/assign`

Assign a specific requester to a test variant (for consistent assignment).

**Request Body**

```json
{
  "assignment_key": "user-xyz"
}
```

**Response `200`**

```json
{
  "test_id": "ab-test-001",
  "variant": "A"
}
```

---

#### `DELETE /api/v1/rules/ab-tests/{test_id}`

Delete an A/B test.

**Response `204`**

---

### Hot Reload

Reload rules into the in-memory registry without restarting the server.

#### `GET /api/v1/rules/hot-reload/status`

Get the current hot reload service status.

**Response `200`** — Dict with reload service state, last reload timestamp, and loaded rule counts.

---

#### `POST /api/v1/rules/hot-reload/reload`

Reload rules from the configured source (database, file, or S3).

**Request Body**

```json
{
  "ruleset_id": "comic-scoring",
  "rule_id": "rule-001",
  "force": false,
  "validate_before_reload": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ruleset_id` | string | No | Reload only a specific ruleset |
| `rule_id` | string | No | Reload only a specific rule |
| `force` | boolean | No | If `true`, bypasses validation checks |
| `validate_before_reload` | boolean | No | Default `true`. Validates rules before applying |

**Response `200`** — Dict with reload result and any validation warnings.

---

#### `POST /api/v1/rules/hot-reload/reload/rule/{rule_id}`

Reload a single rule by ID.

**Response `200`** — Reload result.

---

#### `POST /api/v1/rules/hot-reload/reload/ruleset/{ruleset_id}`

Reload an entire ruleset by name.

**Response `200`** — Reload result.

---

#### `POST /api/v1/rules/hot-reload/validate`

Validate the currently loaded rules (in-memory registry).

**Response `200`** — Validation report with any errors or warnings.

---

#### `POST /api/v1/rules/hot-reload/validate-from-source`

Validate rules from the source (database/file) without reloading them.

**Response `200`** — Validation report.

---

#### `POST /api/v1/rules/hot-reload/monitoring/start`

Start continuous monitoring for rule changes (polls source and auto-reloads on change).

**Response `200`** — Monitoring status.

---

#### `POST /api/v1/rules/hot-reload/monitoring/stop`

Stop continuous monitoring.

**Response `200`** — Monitoring status.

---

#### `GET /api/v1/rules/hot-reload/history`

Get the history of past reload operations.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Number of historical entries to return |

**Response `200`** — Dict with reload history entries.

---

### Consumer Management

Track and manage API consumers (clients) for usage analytics.

#### `GET /consumers`

List consumers.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (`active`, `inactive`) |

**Response `200`**

```json
{
  "consumers": [
    {
      "id": 1,
      "consumer_id": "client-abc",
      "name": "Analytics Service",
      "description": "Internal analytics pipeline",
      "status": "active",
      "tags": ["internal", "analytics"],
      "metadata": {"team": "data"},
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### `GET /consumers/{consumer_id}`

Get a consumer by ID.

**Response `200`** — Single `ConsumerResponse`.

**Response `404`** — Consumer not found.

---

#### `POST /consumers`

Create a consumer.

**Request Body**

```json
{
  "consumer_id": "client-abc",
  "name": "Analytics Service",
  "description": "Internal analytics pipeline",
  "status": "active",
  "tags": ["internal"],
  "metadata": {"team": "data"}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `consumer_id` | string | Yes | Unique consumer identifier |
| `name` | string | Yes | Display name |
| `description` | string | No | Human-readable description |
| `status` | string | No | `"active"` (default) or `"inactive"` |
| `tags` | array of strings | No | Categorization tags |
| `metadata` | object | No | Arbitrary metadata |

**Response `201`** — Created `ConsumerResponse`.

---

#### `PUT /consumers/{consumer_id}`

Update a consumer. All fields optional.

**Response `200`** — Updated `ConsumerResponse`.

---

#### `DELETE /consumers/{consumer_id}`

Delete a consumer.

**Response `204`**

---

#### `POST /consumers/{consumer_id}/rulesets`

Register a consumer to execute a named database ruleset. If the registration already exists but was previously revoked, it is reactivated.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `consumer_id` | string | The consumer's business identifier |

**Request Body**

```json
{
  "ruleset_name": "comic-scoring"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ruleset_name` | string | Yes | Name of the ruleset to register |

**Response `201`** — `ConsumerRulesetRegistrationResponse`

```json
{
  "id": 1,
  "consumer_id": "client-abc",
  "ruleset_id": 5,
  "ruleset_name": "comic-scoring",
  "status": "active",
  "created_at": "2026-04-01T00:00:00Z",
  "updated_at": "2026-04-01T00:00:00Z"
}
```

**Response `400`** — Ruleset not found or validation error.

**Response `404`** — Consumer not found.

---

#### `GET /consumers/{consumer_id}/rulesets`

List ruleset registrations for a consumer.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `consumer_id` | string | The consumer's business identifier |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `active_only` | boolean | `true` | If `true`, return only active registrations. If `false`, include revoked ones. |

**Response `200`**

```json
{
  "registrations": [
    {
      "id": 1,
      "consumer_id": "client-abc",
      "ruleset_id": 5,
      "ruleset_name": "comic-scoring",
      "status": "active",
      "created_at": "2026-04-01T00:00:00Z",
      "updated_at": "2026-04-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

**Response `404`** — Consumer not found.

---

#### `DELETE /consumers/{consumer_id}/rulesets/{ruleset_name}`

Revoke a consumer's registration for a ruleset. The registration record is soft-deleted (status set to `"revoked"`).

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `consumer_id` | string | The consumer's business identifier |
| `ruleset_name` | string | Name of the ruleset to revoke |

**Response `204`**

**Response `404`** — Consumer or registration not found.

---

### Execution History

Query persisted rule execution logs. Useful for auditing, debugging, and analytics.

#### `GET /api/v1/executions`

List execution log rows with optional filters and pagination.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `consumer_id` | string | — | Filter by consumer business identifier |
| `ruleset_id` | integer | — | Filter by ruleset primary key |
| `from` | string (ISO 8601) | — | Inclusive start timestamp (e.g. `2026-01-01T00:00:00Z`) |
| `to` | string (ISO 8601) | — | Exclusive end timestamp |
| `limit` | integer | `100` | Max results to return (1–500) |
| `offset` | integer | `0` | Pagination offset |
| `include_payload` | boolean | `false` | Include `input_data` and `output_data` fields (may contain sensitive data) |

**Response `200`**

```json
{
  "executions": [
    {
      "id": 42,
      "execution_id": "exec-uuid-abc",
      "correlation_id": null,
      "ruleset_id": 5,
      "consumer_id": "client-abc",
      "total_points": 85.0,
      "pattern_result": "YYN",
      "execution_time_ms": 12.5,
      "success": true,
      "error_message": null,
      "timestamp": "2026-04-01T10:00:00Z",
      "input_data": null,
      "output_data": null
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `executions` | array | Matching execution records |
| `total` | integer | Total rows matching filters (before limit/offset) |
| `limit` | integer | Applied limit |
| `offset` | integer | Applied offset |

**`ExecutionLogSummaryResponse` fields**

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Database primary key |
| `execution_id` | string | Unique execution identifier |
| `correlation_id` | string \| null | Request correlation ID (not stored on execution record) |
| `ruleset_id` | integer \| null | Ruleset primary key |
| `consumer_id` | string \| null | Consumer business identifier |
| `total_points` | float \| null | Aggregate score from rule evaluation |
| `pattern_result` | string \| null | Concatenated action results (e.g. `"YYN"`) |
| `execution_time_ms` | float | Duration of rule evaluation in milliseconds |
| `success` | boolean | Whether the execution completed without error |
| `error_message` | string \| null | Error message if `success` is `false` |
| `timestamp` | string \| null | ISO 8601 timestamp when the execution was recorded |
| `input_data` | object \| null | Input payload (only when `include_payload=true`) |
| `output_data` | object \| null | Output payload (only when `include_payload=true`) |

**Example**

```bash
curl "http://localhost:8000/api/v1/executions?consumer_id=client-abc&from=2026-04-01T00:00:00Z&limit=50"
```

**Example with payload**

```bash
curl "http://localhost:8000/api/v1/executions?consumer_id=client-abc&include_payload=true&limit=10"
```

---

### WebSocket

#### `WS /ws/hot-reload`

Subscribe to real-time hot reload events.

Connect via WebSocket to receive JSON notifications whenever rules are reloaded, validated, or monitoring status changes.

**Example (Python)**

```python
import asyncio
import websockets
import json

async def listen():
    async with websockets.connect("ws://localhost:8000/ws/hot-reload") as ws:
        async for message in ws:
            event = json.loads(message)
            print(f"Event type: {event['type']}, payload: {event}")

asyncio.run(listen())
```

**Emitted Event Shape**

```json
{
  "type": "rules_reloaded",
  "timestamp": "2024-01-15T10:30:00Z",
  "ruleset_id": "comic-scoring",
  "rules_count": 5
}
```

---

## Data Models Reference

### `RuleEvaluationResult`

Returned per-rule in dry-run responses.

```typescript
{
  rule_name: string;
  rule_priority?: number;
  condition: string;          // Human-readable condition string
  matched: boolean;
  action_result: string;      // e.g. "Y", "N"
  rule_point: number;
  weight: number;
  execution_time_ms: number;
}
```

### `ErrorResponse`

```typescript
{
  error_type: string;
  message: string;
  error_code?: string;
  context?: Record<string, any>;
  correlation_id?: string;
}
```

### `RuleResponse`

```typescript
{
  id: string;
  rule_name: string;
  type: string;
  conditions: string[];
  description?: string;
  result?: string;
  weight?: number;
  rule_point?: number;
  priority?: number;
  action_result?: string;
}
```

### `WorkflowResponse`

```typescript
{
  name: string;
  description?: string;
  is_active: boolean;
  stages: Array<{ name: string; position: number }>;
  created_at: string;
  updated_at: string;
}
```

### `ConsumerRulesetRegistrationResponse`

```typescript
{
  id: number;                  // Registration primary key
  consumer_id: string;         // Consumer business identifier
  ruleset_id: number;          // Ruleset primary key
  ruleset_name?: string;       // Ruleset name when available
  status: string;              // "active" | "revoked"
  created_at?: string;
  updated_at?: string;
}
```

### `ExecutionLogSummaryResponse`

```typescript
{
  id: number;
  execution_id: string;
  correlation_id?: string;     // Not stored on execution record; reserved
  ruleset_id?: number;
  consumer_id?: string;
  total_points?: number;
  pattern_result?: string;
  execution_time_ms: number;
  success: boolean;
  error_message?: string;
  timestamp?: string;
  input_data?: Record<string, any>;   // Present when include_payload=true
  output_data?: Record<string, any>;  // Present when include_payload=true
}
```

### `ExecutionLogsListResponse`

```typescript
{
  executions: ExecutionLogSummaryResponse[];
  total: number;    // Total matching rows before limit/offset
  limit: number;
  offset: number;
}
```

---

## Configuration Reference

All settings can be supplied as environment variables or in `.env` / `config/config.ini`.

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` | `8000` | Port |
| `API_WORKERS` | `1` | Number of Uvicorn worker processes |
| `ENVIRONMENT` | `dev` | `dev` / `staging` / `prod` |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY_ENABLED` | `false` | Enable API key auth |
| `API_KEY` | — | Secret API key |

### Rule Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `RULES_CONFIG_PATH` | `data/input/rules_config_v4.json` | Local JSON rules file |
| `CONDITIONS_CONFIG_PATH` | `data/input/conditions_config.json` | Local JSON conditions file |
| `USE_DATABASE` | `false` | Use PostgreSQL/TimescaleDB |
| `DATABASE_URL` | — | PostgreSQL connection string |
| `TIMESCALE_SERVICE_URL` | — | Alternative TimescaleDB connection string |
| `S3_BUCKET` | — | S3 bucket name for config storage |
| `S3_CONFIG_PREFIX` | `config/` | S3 key prefix |

### AWS

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region |
| `USE_SSM` | `false` | Load secrets from AWS SSM Parameter Store |
| `SSM_PREFIX` | `/rule-engine/` | SSM parameter key prefix |

### Misc

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL` | `3600` | Cache time-to-live in seconds |
| `MAX_RETRIES` | `3` | Max retries for operations |

**Configuration priority (highest → lowest)**:
1. Environment variables
2. `.env` file
3. `config/config.ini`
4. Built-in defaults

---

## Best Practices

### For Humans

- **Use `dry_run: true`** when testing new rule configurations before going live.
- **Include `correlation_id`** in all requests — it appears in server logs and error responses, making debugging much faster.
- **Use batch endpoint** for bulk processing (more efficient than individual requests). Keep batch sizes under 500 items for predictable latency.
- **Enable API key auth** in production (`API_KEY_ENABLED=true`).
- **Restrict CORS origins** in production (`CORS_ORIGINS=https://your-domain.com`).

### For AI Agents

When integrating with the Rule Engine API:

1. **Discover the schema first** — call `GET /health` to confirm the server is up, then `GET /docs` (or `/openapi.json`) to get the OpenAPI spec if you need the full schema.
2. **Use `correlation_id`** with a unique identifier for every request you make; include it in your own logs to trace calls end-to-end.
3. **Handle partial batch failures** — a `200` response from `/api/v1/rules/batch` does not mean all items succeeded. Always check `results[].status` and `summary.failed_executions`.
4. **Use `dry_run: true` for validation** — before deploying a new rule via the management API, execute it in dry-run mode against sample data to verify it behaves as expected.
5. **Poll hot reload status** via `GET /api/v1/rules/hot-reload/status` after calling reload endpoints to confirm the registry was updated before sending execution requests.
6. **Error handling**: Retry `5xx` errors with exponential backoff. Do not retry `4xx` errors without changing the request.
7. **Management operations require database mode** — CRUD endpoints (`/api/v1/management/*`) only persist changes when `USE_DATABASE=true`. In file-based mode they may only update the in-memory registry.

### Error Retry Strategy

```python
import time
import requests

def execute_with_retry(url, payload, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        if response.status_code < 500:
            # Client error — don't retry
            raise ValueError(response.json().get("message"))
        # Server error — back off and retry
        time.sleep(2 ** attempt)
    raise RuntimeError("Max retries exceeded")
```

---

## Additional Resources

| Resource | URL |
|---------|-----|
| Swagger UI (interactive) | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |
| Health Check | `http://localhost:8000/health` |
| Quick Start Guide | [API_QUICK_START.md](API_QUICK_START.md) |
| Database Setup | [DATABASE_INTEGRATION.md](DATABASE_INTEGRATION.md) |
| Postman Collection | [Rule_Engine_API.postman_collection.json](Rule_Engine_API.postman_collection.json) |
