# Rule Engine API Documentation

REST API for executing business rules and workflows.

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [API Endpoints](#api-endpoints)
  - [Health Check](#health-check)
  - [Rule Execution](#rule-execution)
  - [Batch Rule Execution](#batch-rule-execution)
  - [Workflow Execution](#workflow-execution)
- [Authentication](#authentication)
- [Request/Response Models](#requestresponse-models)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [API Versioning](#api-versioning)

## Overview

The Rule Engine API provides REST endpoints for:
- **Rule Execution**: Execute business rules against input data
- **Batch Rule Execution**: Process multiple data items efficiently
- **Workflow Execution**: Execute multi-stage workflows
- **Health Checks**: Monitor API service status

### Base URL

Default base URL: `http://localhost:8000`

### API Version

Current API version: `v1`

All endpoints are prefixed with `/api/v1` except health and root endpoints.

## Getting Started

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (optional):
```bash
export API_HOST=0.0.0.0
export API_PORT=8000
export API_KEY_ENABLED=false
```

3. Start the API server:
```bash
python run_api.py
```

Or using uvicorn directly:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Interactive API Documentation

Once the server is running, access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Health Check

#### `GET /health`

Check the health status of the API service.

**Description**: This endpoint provides basic health information about the API service, including status, version, uptime, and environment information. It does not require authentication and can be used for monitoring and load balancer health checks.

**Parameters**: None

**Request Headers**:
- `Content-Type`: `application/json` (optional)
- `X-API-Key`: API key (optional, only if authentication is enabled)

**Response**: `200 OK`

**Response Body**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600.0,
  "environment": "production"
}
```

**Response Fields**:
- `status` (string, required): Health status - `"healthy"` or `"unhealthy"`
- `version` (string, required): API version number
- `timestamp` (datetime, required): Current server timestamp in UTC
- `uptime_seconds` (float, optional): Application uptime in seconds
- `environment` (string, optional): Environment name (dev/staging/production)

**Example Request**:
```bash
curl http://localhost:8000/health
```

**Example Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "uptime_seconds": 3600.5,
  "environment": "production"
}
```

---

#### `GET /`

Root endpoint that provides API information.

**Description**: Returns basic API information including name, version, and links to documentation endpoints.

**Parameters**: None

**Response**: `200 OK`

**Response Body**:
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

### Rule Execution

#### `POST /api/v1/rules/execute`

Execute business rules against input data.

**Description**: Evaluates all configured business rules against the provided input data and returns scoring results with action recommendations. This endpoint supports both normal execution and dry-run mode for testing.

**Request Headers**:
- `Content-Type`: `application/json` (required)
- `X-API-Key`: API key (optional, required if authentication is enabled)
- `X-Correlation-ID`: Correlation ID for tracing (optional)

**Request Body**:
```json
{
  "data": {
    "issue": 35,
    "title": "Superman",
    "publisher": "DC"
  },
  "dry_run": false,
  "correlation_id": "req-12345"
}
```

**Request Fields**:
- `data` (object, required): Input data dictionary for rule evaluation. The structure depends on your rule configuration.
- `dry_run` (boolean, optional): If `true`, executes rules without side effects and returns detailed rule evaluation information. Default: `false`
- `correlation_id` (string, optional): Correlation ID for request tracing. If not provided, the API will generate one.

**Response**: `200 OK`

**Response Body** (normal execution):
```json
{
  "total_points": 1050.0,
  "pattern_result": "YYY",
  "action_recommendation": "Approved",
  "dry_run": false,
  "execution_time_ms": 45.2,
  "correlation_id": "req-12345"
}
```

**Response Body** (dry run mode):
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
  "would_match": [
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
  "would_not_match": [
    {
      "rule_name": "Rule 2",
      "rule_priority": 2,
      "condition": "title equals 'Batman'",
      "matched": false,
      "action_result": "N",
      "rule_point": 0.0,
      "weight": 25.0,
      "execution_time_ms": 1.2
    }
  ],
  "dry_run": true,
  "execution_time_ms": 45.2,
  "correlation_id": "req-12345"
}
```

**Response Fields**:
- `total_points` (float, required): Sum of weighted rule points from all matched rules
- `pattern_result` (string, required): Concatenated action results from matched rules (e.g., "YYY", "YNN")
- `action_recommendation` (string, optional): Recommended action based on pattern matching
- `rule_evaluations` (array, optional): Detailed evaluation results for each rule. Only included when `dry_run: true`
- `would_match` (array, optional): Rules that matched. Only included when `dry_run: true`
- `would_not_match` (array, optional): Rules that didn't match. Only included when `dry_run: true`
- `dry_run` (boolean, optional): Indicates whether this was a dry run execution
- `execution_time_ms` (float, optional): Total execution time in milliseconds
- `correlation_id` (string, optional): Correlation ID for tracing

**Error Responses**:
- `400 Bad Request`: Invalid input data format
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error during rule execution

---

#### `POST /api/v1/rules/batch`

Execute rules against multiple data items in batch.

**Description**: Processes multiple input data items efficiently, optionally in parallel. This endpoint is optimized for batch processing scenarios where you need to evaluate rules for many items at once. Each item is processed independently, and failures in one item don't affect others.

**Request Headers**:
- `Content-Type`: `application/json` (required)
- `X-API-Key`: API key (optional, required if authentication is enabled)
- `X-Correlation-ID`: Correlation ID for batch tracking (optional)

**Request Body**:
```json
{
  "data_list": [
    {"issue": 35, "title": "Superman", "publisher": "DC"},
    {"issue": 10, "title": "Batman", "publisher": "DC"}
  ],
  "dry_run": false,
  "max_workers": 4,
  "correlation_id": "batch-12345"
}
```

**Request Fields**:
- `data_list` (array, required): List of input data dictionaries. Each dictionary represents one item to process. Must contain at least one item.
- `dry_run` (boolean, optional): If `true`, executes rules without side effects. Default: `false`
- `max_workers` (integer, optional): Maximum number of parallel workers for processing. If not specified or `null`, the system will automatically determine the optimal number. Must be positive if provided.
- `correlation_id` (string, optional): Correlation ID for batch tracking. If not provided, the API will generate one.

**Response**: `200 OK`

**Response Body**:
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
      "status": "success",
      "total_points": 800.0,
      "pattern_result": "Y--",
      "action_recommendation": "Rejected"
    }
  ],
  "summary": {
    "total_executions": 2,
    "successful_executions": 2,
    "failed_executions": 0,
    "total_execution_time_ms": 89.5,
    "avg_execution_time_ms": 44.75,
    "success_rate": 100.0
  },
  "dry_run": false
}
```

**Response Fields**:
- `batch_id` (string, required): Unique identifier for this batch execution
- `results` (array, required): List of execution results, one per input item. Order matches the input `data_list` order.
  - `item_index` (integer): Zero-based index of the item in the input list
  - `correlation_id` (string): Correlation ID for this specific item
  - `status` (string): Execution status - `"success"` or `"failed"`
  - `total_points` (float, optional): Sum of weighted rule points (only if successful)
  - `pattern_result` (string, optional): Concatenated action results (only if successful)
  - `action_recommendation` (string, optional): Recommended action (only if successful)
  - `error` (string, optional): Error message (only if failed)
  - `error_type` (string, optional): Error type/class name (only if failed)
- `summary` (object, required): Batch execution summary statistics
  - `total_executions` (integer): Total number of items processed
  - `successful_executions` (integer): Number of successfully processed items
  - `failed_executions` (integer): Number of failed items
  - `total_execution_time_ms` (float): Total execution time for the batch in milliseconds
  - `avg_execution_time_ms` (float): Average execution time per item in milliseconds
  - `success_rate` (float): Success rate as a percentage (0-100)
- `dry_run` (boolean, optional): Indicates whether this was a dry run execution

**Error Responses**:
- `400 Bad Request`: Invalid input data (e.g., empty data_list, invalid max_workers)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error during batch processing

**Performance Notes**:
- Batch processing uses parallel execution when `max_workers > 1`
- The optimal `max_workers` value depends on your system resources and rule complexity
- Large batches (1000+ items) may take significant time - consider processing in smaller batches
- Individual item failures are captured in the results but don't stop batch processing

---

### Workflow Execution

#### `POST /api/v1/workflow/execute`

Execute a multi-stage workflow.

**Description**: Executes a multi-stage workflow using the Chain of Responsibility pattern. Each stage processes the data through its handler and passes the result to the next stage. This is useful for complex business processes that require sequential processing across multiple stages.

**Request Headers**:
- `Content-Type`: `application/json` (required)
- `X-API-Key`: API key (optional, required if authentication is enabled)
- `X-Correlation-ID`: Correlation ID for tracing (optional)

**Request Body**:
```json
{
  "process_name": "ticket_processing",
  "stages": ["NEW", "INPROGESS", "FINISHED"],
  "data": {
    "ticket_id": "TICK-123",
    "title": "Issue Report",
    "priority": "high"
  }
}
```

**Request Fields**:
- `process_name` (string, required): Name of the process/workflow to execute. Must be a non-empty string.
- `stages` (array, optional): List of workflow stage names to execute in order. If not provided, default stages will be used: `["NEW", "INPROGESS", "FINISHED"]`. Each stage must be a non-empty string.
- `data` (object, optional): Input data dictionary to process through the workflow. Defaults to empty dictionary.

**Response**: `200 OK`

**Response Body**:
```json
{
  "process_name": "ticket_processing",
  "stages": ["NEW", "INPROGESS", "FINISHED"],
  "result": {
    "status": "completed",
    "data": {
      "ticket_id": "TICK-123",
      "state": "FINISHED"
    }
  },
  "execution_time_ms": 123.5
}
```

**Response Fields**:
- `process_name` (string, required): Name of the executed process/workflow
- `stages` (array, required): List of stages that were executed
- `result` (object, optional): Final workflow result. Structure depends on the workflow handlers.
- `execution_time_ms` (float, optional): Total execution time in milliseconds

**Error Responses**:
- `400 Bad Request`: Invalid input (e.g., empty process_name, invalid stage names)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Workflow execution error

**Workflow Stages**:
The workflow system uses handlers for each stage:
- `NEW`: NewCaseHandler - handles new case initialization
- `INPROGESS`: InProcessCaseHandler - handles in-progress case processing
- `FINISHED`: FinishedCaseHandler - handles finished case processing

Custom stages can be configured based on your workflow requirements.

## Authentication

API key authentication is **optional** and can be enabled via environment variables.

### Enable API Key Authentication

1. Set environment variables:
```bash
export API_KEY_ENABLED=true
export API_KEY=your-secret-api-key
```

2. Include API key in requests:
```bash
curl -H "X-API-Key: your-secret-api-key" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/api/v1/rules/execute \
     -d '{"data": {...}}'
```

### Disable API Key Authentication (Default)

By default, API key authentication is disabled. To explicitly disable:

```bash
export API_KEY_ENABLED=false
```

## Request/Response Models

### Rule Execution Request

**Model**: `RuleExecutionRequest`

```typescript
{
  data: { [key: string]: any };      // Required: Input data dictionary
  dry_run?: boolean;                  // Optional: Default false
  correlation_id?: string;            // Optional: Correlation ID for tracing
}
```

**Field Details**:
- `data` (object, required): Dictionary containing input data for rule evaluation. The structure and fields depend on your configured rules.
- `dry_run` (boolean, optional): If `true`, executes rules without side effects and returns detailed evaluation information. Default: `false`
- `correlation_id` (string, optional): Correlation ID for request tracing. If not provided, the API generates one automatically.

### Rule Execution Response

**Model**: `RuleExecutionResponse`

```typescript
{
  total_points: number;                              // Required: Sum of weighted points
  pattern_result: string;                           // Required: Concatenated action results
  action_recommendation?: string;                    // Optional: Recommended action
  rule_evaluations?: RuleEvaluationResult[];       // Optional: Detailed evaluations (dry_run only)
  would_match?: RuleEvaluationResult[];            // Optional: Matched rules (dry_run only)
  would_not_match?: RuleEvaluationResult[];        // Optional: Unmatched rules (dry_run only)
  dry_run?: boolean;                                // Optional: Whether this was dry run
  execution_time_ms?: number;                       // Optional: Execution time in ms
  correlation_id?: string;                          // Optional: Correlation ID
}
```

**Rule Evaluation Result**:
```typescript
{
  rule_name: string;                 // Rule name
  rule_priority?: number;            // Rule priority (optional)
  condition: string;                  // Condition string
  matched: boolean;                   // Whether rule matched
  action_result: string;              // Action result (e.g., "Y", "N")
  rule_point: number;                 // Points for this rule
  weight: number;                     // Weight of this rule
  execution_time_ms: number;         // Execution time for this rule
}
```

### Batch Rule Execution Request

**Model**: `BatchRuleExecutionRequest`

```typescript
{
  data_list: { [key: string]: any }[];  // Required: List of data dictionaries (min 1 item)
  dry_run?: boolean;                     // Optional: Default false
  max_workers?: number;                  // Optional: Max parallel workers (must be positive)
  correlation_id?: string;               // Optional: Correlation ID for batch tracking
}
```

**Field Details**:
- `data_list` (array, required): List of input data dictionaries. Each dictionary represents one item to process. Must contain at least one item. All items must be dictionaries.
- `dry_run` (boolean, optional): If `true`, executes rules without side effects. Default: `false`
- `max_workers` (integer, optional): Maximum number of parallel workers. If `null` or not provided, the system automatically determines the optimal number. Must be positive if provided.
- `correlation_id` (string, optional): Correlation ID for batch tracking. If not provided, the API generates one automatically.

### Batch Rule Execution Response

**Model**: `BatchRuleExecutionResponse`

```typescript
{
  batch_id: string;                   // Required: Batch execution ID
  results: BatchItemResult[];         // Required: List of results (one per item)
  summary: {                           // Required: Batch summary statistics
    total_executions: number;
    successful_executions: number;
    failed_executions: number;
    total_execution_time_ms: number;
    avg_execution_time_ms: number;
    success_rate: number;              // Percentage (0-100)
  };
  dry_run?: boolean;                   // Optional: Whether this was dry run
}
```

**Batch Item Result**:
```typescript
{
  item_index: number;                 // Zero-based index
  correlation_id: string;              // Item correlation ID
  status: string;                      // "success" or "failed"
  total_points?: number;               // Only if successful
  pattern_result?: string;             // Only if successful
  action_recommendation?: string;      // Only if successful
  error?: string;                      // Only if failed
  error_type?: string;                 // Only if failed
}
```

### Workflow Execution Request

**Model**: `WorkflowExecutionRequest`

```typescript
{
  process_name: string;                // Required: Process/workflow name (non-empty)
  stages?: string[];                    // Optional: Stage names (default: ["NEW", "INPROGESS", "FINISHED"])
  data?: { [key: string]: any };       // Optional: Input data (default: {})
}
```

**Field Details**:
- `process_name` (string, required): Name of the process/workflow to execute. Must be a non-empty string after trimming.
- `stages` (array, optional): List of workflow stage names to execute in order. Each stage must be a non-empty string. Defaults to `["NEW", "INPROGESS", "FINISHED"]` if not provided.
- `data` (object, optional): Input data dictionary to process through the workflow. Defaults to empty dictionary if not provided.

### Workflow Execution Response

**Model**: `WorkflowExecutionResponse`

```typescript
{
  process_name: string;                // Required: Process name
  stages: string[];                    // Required: Executed stages
  result?: { [key: string]: any };     // Optional: Final workflow result
  execution_time_ms?: number;          // Optional: Execution time in ms
}
```

### Health Response

**Model**: `HealthResponse`

```typescript
{
  status: string;                      // Required: "healthy" or "unhealthy"
  version: string;                     // Required: API version
  timestamp: string;                   // Required: UTC timestamp (ISO 8601)
  uptime_seconds?: number;            // Optional: Uptime in seconds
  environment?: string;               // Optional: Environment name
}
```

### Error Response

**Model**: `ErrorResponse`

```typescript
{
  error_type: string;                 // Required: Error class name
  message: string;                     // Required: Human-readable message
  error_code?: string;                 // Optional: Error code for programmatic handling
  context?: { [key: string]: any };    // Optional: Additional error context
  correlation_id?: string;             // Optional: Correlation ID for tracing
}
```

## Error Handling

All errors follow a standardized format to ensure consistent error handling across the API.

### Error Response Format

```json
{
  "error_type": "ErrorClassName",
  "message": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "context": {
    "additional": "context",
    "field_name": "field_value"
  },
  "correlation_id": "req-12345"
}
```

### HTTP Status Codes

| Status Code | Description | When It Occurs |
|------------|-------------|----------------|
| `200 OK` | Request successful | Operation completed successfully |
| `400 Bad Request` | Invalid input data | Data validation failed, invalid format |
| `401 Unauthorized` | Authentication required | API key missing or required but not provided |
| `403 Forbidden` | Access denied | Invalid API key provided |
| `422 Unprocessable Entity` | Validation error | Request format valid but data validation failed |
| `500 Internal Server Error` | Server error | Internal processing error, configuration issues |

### Error Types

#### DataValidationError (400)

Occurs when input data is invalid or missing required fields.

**Example**:
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

#### ConfigurationError (500)

Occurs when there's a configuration issue that prevents rule execution.

**Example**:
```json
{
  "error_type": "ConfigurationError",
  "message": "Rules configuration file not found",
  "error_code": "CONFIG_FILE_NOT_FOUND",
  "context": {
    "config_path": "data/input/rules_config_v4.json"
  },
  "correlation_id": "req-12345"
}
```

#### RuleEvaluationError (500)

Occurs when rule evaluation fails due to an error in rule logic or execution.

**Example**:
```json
{
  "error_type": "RuleEvaluationError",
  "message": "Error evaluating rule: Rule 1",
  "error_code": "RULE_EVALUATION_FAILED",
  "context": {
    "rule_name": "Rule 1",
    "rule_index": 0
  },
  "correlation_id": "req-12345"
}
```

#### WorkflowError (500)

Occurs when workflow execution fails.

**Example**:
```json
{
  "error_type": "WorkflowError",
  "message": "Workflow stage handler not found",
  "error_code": "WORKFLOW_HANDLER_NOT_FOUND",
  "context": {
    "stage": "CUSTOM_STAGE",
    "process_name": "ticket_processing"
  },
  "correlation_id": "req-12345"
}
```

### Error Handling Best Practices

1. **Always check the HTTP status code** first before parsing the response body
2. **Check the `error_code` field** for programmatic error handling
3. **Use `correlation_id`** for debugging and support requests
4. **Check the `context` field** for additional error details
5. **Implement retry logic** for 500 errors with exponential backoff
6. **Validate input data** before sending requests to avoid 400/422 errors
7. **Handle 401/403 errors** by checking API key configuration

### Client-Side Error Handling Example

```python
import requests
from requests.exceptions import RequestException

try:
    response = requests.post(
        'http://localhost:8000/api/v1/rules/execute',
        json={'data': {'issue': 35, 'title': 'Superman'}}
    )
    response.raise_for_status()
    result = response.json()
    print(f"Success: {result['total_points']}")
except requests.HTTPError as e:
    if e.response.status_code == 400:
        error = e.response.json()
        print(f"Validation Error: {error['message']}")
    elif e.response.status_code == 500:
        error = e.response.json()
        print(f"Server Error: {error['message']}")
        print(f"Correlation ID: {error.get('correlation_id')}")
except RequestException as e:
    print(f"Request failed: {e}")
```

## Examples

### Example 1: Execute Rules

```bash
curl -X POST http://localhost:8000/api/v1/rules/execute \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "issue": 35,
      "title": "Superman",
      "publisher": "DC"
    }
  }'
```

### Example 2: Execute Rules with Dry Run

```bash
curl -X POST http://localhost:8000/api/v1/rules/execute \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "issue": 35,
      "title": "Superman",
      "publisher": "DC"
    },
    "dry_run": true
  }'
```

### Example 3: Batch Rule Execution

```bash
curl -X POST http://localhost:8000/api/v1/rules/batch \
  -H "Content-Type: application/json" \
  -d '{
    "data_list": [
      {"issue": 35, "title": "Superman", "publisher": "DC"},
      {"issue": 10, "title": "Batman", "publisher": "DC"}
    ],
    "max_workers": 4
  }'
```

### Example 4: Execute Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "process_name": "ticket_processing",
    "stages": ["NEW", "INPROGESS", "FINISHED"],
    "data": {
      "ticket_id": "TICK-123",
      "title": "Issue Report"
    }
  }'
```

### Example 5: Python Client

```python
import requests

# Execute rules
response = requests.post(
    'http://localhost:8000/api/v1/rules/execute',
    json={
        'data': {
            'issue': 35,
            'title': 'Superman',
            'publisher': 'DC'
        }
    }
)

result = response.json()
print(f"Total Points: {result['total_points']}")
print(f"Action: {result['action_recommendation']}")
```

### Example 6: Python Client with API Key

```python
import requests

# Execute rules with API key
response = requests.post(
    'http://localhost:8000/api/v1/rules/execute',
    headers={'X-API-Key': 'your-secret-api-key'},
    json={
        'data': {
            'issue': 35,
            'title': 'Superman',
            'publisher': 'DC'
        }
    }
)

result = response.json()
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Server host address |
| `API_PORT` | `8000` | Server port |
| `API_WORKERS` | `1` | Number of worker processes |
| `API_KEY_ENABLED` | `false` | Enable API key authentication |
| `API_KEY` | - | API key for authentication (required if enabled) |
| `CORS_ORIGINS` | `*` | CORS allowed origins (comma-separated) |
| `ENVIRONMENT` | `dev` | Environment name (dev/staging/prod) |
| `LOG_LEVEL` | `INFO` | Logging level |

### Configuration File

Configuration can also be managed through `config/config.ini` or environment variables as described in the main README.

## Correlation IDs

All requests can include an optional `correlation_id` for tracing. If not provided, the API automatically generates one.

The correlation ID is:
- Included in all response headers as `X-Correlation-ID`
- Included in all log entries
- Returned in error responses

### Using Correlation IDs

```bash
# Request with correlation ID
curl -X POST http://localhost:8000/api/v1/rules/execute \
  -H "X-Correlation-ID: my-custom-id" \
  -H "Content-Type: application/json" \
  -d '{"data": {...}}'

# Response includes correlation ID in header and body
# X-Correlation-ID: my-custom-id
```

## Rate Limiting

Rate limiting is not currently implemented but can be added using middleware if needed.

## CORS

CORS is enabled by default for all origins. To restrict origins:

```bash
export CORS_ORIGINS=https://example.com,https://api.example.com
```

## Logging

All API requests and responses are logged with:
- Request method, path, query parameters
- Response status code
- Execution time
- Correlation ID
- Client IP address

## Best Practices

### Request Handling

1. **Always use HTTPS** in production environments
2. **Include correlation IDs** in all requests for better traceability
3. **Use appropriate timeouts** for API requests (recommended: 30-60 seconds)
4. **Implement retry logic** with exponential backoff for transient errors
5. **Validate input data** before sending to the API

### Batch Processing

1. **Use batch endpoint** for processing multiple items (more efficient than individual requests)
2. **Set appropriate `max_workers`** based on your system resources
3. **Process large batches in chunks** (recommended: 100-500 items per batch)
4. **Monitor batch summary statistics** to track success rates and performance

### Performance

1. **Use dry run mode** for testing rule configurations
2. **Cache rule configurations** when possible to reduce initialization overhead
3. **Monitor execution times** using the `execution_time_ms` field in responses
4. **Use connection pooling** when making multiple requests

### Security

1. **Enable API key authentication** in production environments
2. **Store API keys securely** (use environment variables or secret management systems)
3. **Never commit API keys** to version control
4. **Use HTTPS** to encrypt data in transit
5. **Validate and sanitize input data** before sending to the API

### Error Handling

1. **Implement comprehensive error handling** for all error status codes
2. **Log correlation IDs** for debugging purposes
3. **Handle partial failures** in batch processing appropriately
4. **Implement circuit breakers** for repeated failures

## API Versioning

### Current Version: v1

The API uses URL-based versioning. The current version is `v1`, accessible at `/api/v1/*`.

### Version Compatibility

- API version `v1` is the current stable version
- Breaking changes will result in a new version number
- Previous versions will be maintained for a deprecation period
- Version information is available in:
  - Health endpoint: `/health`
  - Root endpoint: `/`
  - OpenAPI specification: `/openapi.json`

### Future Versions

When breaking changes are introduced:
1. A new version number will be assigned (e.g., `v2`)
2. Previous versions will remain available
3. A deprecation notice will be included in responses
4. Migration guides will be provided

## Rate Limiting

**Current Status**: Rate limiting is not currently implemented.

### Recommendations

For production deployments, consider:
- Implementing rate limiting at the load balancer or API gateway level
- Using middleware for rate limiting if needed
- Monitoring API usage patterns
- Setting appropriate limits based on your use case

## CORS

Cross-Origin Resource Sharing (CORS) is enabled by default for all origins.

### Configuration

To restrict CORS origins:

```bash
export CORS_ORIGINS=https://example.com,https://api.example.com
```

**Security Note**: Using `*` (default) allows all origins. In production, restrict to specific domains.

## Logging

All API requests and responses are automatically logged with:
- Request method, path, and query parameters
- Response status code
- Execution time
- Correlation ID
- Client IP address
- Error details (if any)

Logs follow structured logging format and can be configured via environment variables:
- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `ENVIRONMENT`: Set environment name for log context

## Support

For issues or questions:
- Review the main [README](README.MD)
- Check interactive API documentation at `/docs`
- Review error responses for detailed error information
- Check [API_QUICK_START.md](API_QUICK_START.md) for quick start guide

## Additional Resources

- **Interactive API Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI Specification**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

