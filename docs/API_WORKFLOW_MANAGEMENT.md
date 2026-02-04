## Workflow Management API

This document specifies the HTTP APIs for **managing workflows** and **executing workflows by name**.

- **Base path**: `/api/v1`
- **Auth**: `X-API-Key` header (validated by existing auth middleware)
- **Scope**: Workflows are **global** (not tenant-specific) and persisted in the database.

---

## Common Models

### ErrorResponse

All error responses use the existing `ErrorResponse` schema:

- **error_type**: `string` – Error type/class name (e.g. `DataValidationError`)
- **message**: `string` – Human-readable error message
- **error_code**: `string | null` – Machine-readable error code
- **context**: `object | null` – Additional context
- **correlation_id**: `string | null` – Correlation ID for tracing

Errors are returned with standard HTTP status codes (400, 404, 500, etc.).

---

## Workflow Definition Models

### WorkflowStageModel (response)

Represents a single stage in a workflow definition.

- **name**: `string` – Stage name (e.g. `NEW`, `INPROGESS`, `FINISHED`)
- **position**: `integer` – 1-based order of the stage within the workflow

Example:

```json
{
  "name": "NEW",
  "position": 2
}
```

### WorkflowCreateRequest

Request body for creating a workflow.

- **name**: `string` – Unique workflow name, non-empty, trimmed
- **description**: `string | null` – Optional description
- **stages**: `string[]` – Non-empty list of stage names
  - Each stage must be a non-empty string after trimming

Example:

```json
{
  "name": "ticket_processing",
  "description": "Standard ticket workflow",
  "stages": ["INITIATED", "NEW", "INPROGESS", "FINISHED"]
}
```

### WorkflowUpdateRequest

Request body for updating a workflow.

- **description**: `string | null` – New description (optional)
- **stages**: `string[] | null` – New ordered list of stages (optional)
  - If provided, replaces the existing stage list
  - Same validation rules as in `WorkflowCreateRequest`
- **is_active**: `boolean | null` – Activate/deactivate workflow (soft delete)

Example:

```json
{
  "description": "Updated ticket workflow",
  "stages": ["NEW", "INPROGESS", "FINISHED"],
  "is_active": true
}
```

### WorkflowResponse

Response model for a single workflow.

- **name**: `string` – Workflow name
- **description**: `string | null`
- **is_active**: `boolean`
- **stages**: `WorkflowStageModel[]`
- **created_at**: `string` (ISO 8601)
- **updated_at**: `string` (ISO 8601)

Example:

```json
{
  "name": "ticket_processing",
  "description": "Standard ticket workflow",
  "is_active": true,
  "stages": [
    { "name": "INITIATED", "position": 1 },
    { "name": "NEW", "position": 2 },
    { "name": "INPROGESS", "position": 3 },
    { "name": "FINISHED", "position": 4 }
  ],
  "created_at": "2026-02-04T10:00:00Z",
  "updated_at": "2026-02-04T10:05:00Z"
}
```

### WorkflowsListResponse

Response model for listing workflows.

- **workflows**: `WorkflowResponse[]`
- **count**: `integer` – Total number of workflows in the current result

Example:

```json
{
  "workflows": [
    {
      "name": "ticket_processing",
      "description": "Standard ticket workflow",
      "is_active": true,
      "stages": [
        { "name": "INITIATED", "position": 1 },
        { "name": "NEW", "position": 2 }
      ],
      "created_at": "2026-02-04T10:00:00Z",
      "updated_at": "2026-02-04T10:05:00Z"
    }
  ],
  "count": 1
}
```

---

## Execution Models

### WorkflowExecutionResponse (existing)

Used by both ad-hoc execution and execute-by-name.

- **process_name**: `string` – Name of the process/workflow
- **stages**: `string[]` – List of executed stage names
- **result**: `object | null` – Final workflow result (typically includes a `data` field)
- **execution_time_ms**: `number | null` – Total execution time in milliseconds

Example:

```json
{
  "process_name": "ticket_processing",
  "stages": ["INITIATED", "NEW", "INPROGESS", "FINISHED"],
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

### WorkflowNamedExecutionRequest

Request model for executing a workflow by its name.

- **workflow_name**: `string` – Name of the workflow definition to execute
- **data**: `object` – Input data passed to the workflow handlers

Example:

```json
{
  "workflow_name": "ticket_processing",
  "data": {
    "ticket_id": "TICK-123",
    "title": "Issue Report",
    "priority": "high"
  }
}
```

---

## Endpoints

### 1. Create workflow

- **Method**: `POST`
- **Path**: `/api/v1/workflows`
- **Auth**: `X-API-Key` required
- **Request body**: `WorkflowCreateRequest`

**Responses**:

- `201 Created` – Body: `WorkflowResponse`
- `400 Bad Request` – Invalid payload or duplicate name (`DataValidationError` via `ErrorResponse`)
- `500 Internal Server Error` – `WorkflowError` or unexpected

---

### 2. List workflows

- **Method**: `GET`
- **Path**: `/api/v1/workflows`
- **Auth**: `X-API-Key` required

**Query parameters**:

- **is_active**: `boolean` (optional) – Filter by active flag. Default: all workflows.
- **offset**: `integer` (optional) – Pagination offset. Default: `0`.
- **limit**: `integer` (optional) – Page size. Default: `50`, max recommended: `200`.

**Responses**:

- `200 OK` – Body: `WorkflowsListResponse`

---

### 3. Get workflow by name

- **Method**: `GET`
- **Path**: `/api/v1/workflows/{name}`
- **Auth**: `X-API-Key` required

**Path parameter**:

- **name**: `string` – URL-encoded workflow name

**Responses**:

- `200 OK` – Body: `WorkflowResponse`
- `404 Not Found` – Workflow not found (inactive or missing)

---

### 4. Update workflow

- **Method**: `PUT`
- **Path**: `/api/v1/workflows/{name}`
- **Auth**: `X-API-Key` required

**Path parameter**:

- **name**: `string` – Existing workflow name

**Request body**: `WorkflowUpdateRequest`

**Semantics**:

- If `stages` is provided:
  - Replace the complete stage list.
  - Recompute positions from 1..N in the given order.
- If `is_active` is provided:
  - Toggle workflow active flag (soft enable/disable).

**Responses**:

- `200 OK` – Body: `WorkflowResponse`
- `400 Bad Request` – Invalid stages, empty payload, etc.
- `404 Not Found` – Workflow not found

---

### 5. Delete (deactivate) workflow

- **Method**: `DELETE`
- **Path**: `/api/v1/workflows/{name}`
- **Auth**: `X-API-Key` required

**Path parameter**:

- **name**: `string` – Workflow name

**Semantics**:

- By default, performs a **soft delete** (`is_active = false`).
- Optionally, an implementation may support a query flag such as `?hard=true` to hard-delete the workflow and its stages. Recommended default is soft delete to preserve history.

**Responses**:

- `204 No Content` – Success (idempotent: deleting an already inactive workflow may still return 204)
- `404 Not Found` – Workflow not found

---

### 6. Execute workflow by name (new)

- **Method**: `POST`
- **Path**: `/api/v1/workflow/execute-by-name`
- **Auth**: `X-API-Key` required

**Request body**: `WorkflowNamedExecutionRequest`

**Behavior**:

1. Look up workflow definition by `workflow_name` (must be `is_active = true`).
2. Extract ordered stage names from the definition.
3. Invoke existing engine:
   - `wf_exec(process_name=workflow_name, ls_stages=stages, data=data)`
4. Return `WorkflowExecutionResponse`.

**Responses**:

- `200 OK` – Body: `WorkflowExecutionResponse`
- `400 Bad Request` – Invalid payload (`workflow_name` empty, `data` not an object, etc.)
- `404 Not Found` – Workflow not found or inactive
- `500 Internal Server Error` – `WorkflowError` or unexpected

Example success response:

```json
{
  "process_name": "ticket_processing",
  "stages": ["INITIATED", "NEW", "INPROGESS", "FINISHED"],
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

---

### 7. Existing ad-hoc execution (unchanged)

The existing endpoint for ad-hoc workflow execution remains available:

- **Method**: `POST`
- **Path**: `/api/v1/workflow/execute`
- **Auth**: `X-API-Key` required

**Request body** (existing `WorkflowExecutionRequest`):

- **process_name**: `string`
- **stages**: `string[]` (optional)
  - If empty, defaults to `["INITIATED", "NEW", "INPROGESS", "FINISHED"]`.
- **data**: `object`

**Response**:

- `200 OK` – `WorkflowExecutionResponse`
- Error responses as per `ErrorResponse`.

This endpoint directly uses the provided `stages` instead of loading them from a stored workflow definition.

