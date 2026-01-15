# DMN Rules Execution API Specification

## Overview

This specification defines the API endpoints for executing business rules directly from DMN (Decision Model Notation) files. This feature allows users to execute rules without pre-configuring them in the system, providing flexibility for ad-hoc rule execution and testing.

## Table of Contents

- [Overview](#overview)
- [API Endpoints](#api-endpoints)
- [Request/Response Models](#requestresponse-models)
- [DMN File Format](#dmn-file-format)
- [Rule Execution Flow](#rule-execution-flow)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Limitations](#limitations)

## API Endpoints

### 1. Execute Rules from DMN File

#### `POST /api/v1/rules/execute-dmn`

Execute business rules from a DMN file against input data.

**Description**: This endpoint accepts a DMN file (via file path, file upload, or XML content) and input data, parses the DMN file to extract decision tables and rules, converts them to executable format, and executes them against the provided input data.

**Endpoint**: `/api/v1/rules/execute-dmn`

**Method**: `POST`

**Content-Type**: `application/json`

**Authentication**: Optional (if `API_KEY_ENABLED=true`)

**Request Body**: `DMNRuleExecutionRequest`

**Response**: `200 OK` with `RuleExecutionResponse`

**Response Codes**:
- `200 OK`: Rules executed successfully
- `400 Bad Request`: Invalid request (missing data, invalid DMN, etc.)
- `401 Unauthorized`: Missing or invalid API key (if authentication enabled)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error during execution

---

### 2. Execute Rules from DMN File Upload

#### `POST /api/v1/rules/execute-dmn-upload`

Execute business rules from an uploaded DMN file against input data.

**Description**: This endpoint accepts a DMN file as multipart form data upload along with input data, providing a simpler interface for file-based execution.

**Endpoint**: `/api/v1/rules/execute-dmn-upload`

**Method**: `POST`

**Content-Type**: `multipart/form-data`

**Authentication**: Optional (if `API_KEY_ENABLED=true`)

**Request Parameters**:
- `file` (required): DMN XML file (`.dmn` extension)
- `data` (required): JSON string containing input data
- `dry_run` (optional): Boolean flag for dry run mode (default: `false`)
- `correlation_id` (optional): Correlation ID for request tracing

**Response**: `200 OK` with `RuleExecutionResponse`

**Response Codes**: Same as `/execute-dmn`

---

## Request/Response Models

### DMNRuleExecutionRequest

Request model for DMN rule execution.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dmn_file` | `string` | No* | Path to DMN file (relative to data/input or absolute path) |
| `dmn_content` | `string` | No* | DMN XML content as string |
| `data` | `Dict[str, Any]` | Yes | Input data dictionary for rule evaluation |
| `dry_run` | `boolean` | No | Execute rules without side effects (default: `false`) |
| `correlation_id` | `string` | No | Correlation ID for request tracing |

\* Exactly one of `dmn_file`, `dmn_content`, or `file` (upload) must be provided.

**Example Request**:

```json
{
  "dmn_file": "data/input/sample_rules.dmn",
  "data": {
    "season": "Fall",
    "guests": 6
  },
  "dry_run": false,
  "correlation_id": "req-12345"
}
```

**Alternative with XML Content**:

```json
{
  "dmn_content": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
  "data": {
    "season": "Winter",
    "guests": 5
  },
  "dry_run": true
}
```

---

### RuleExecutionResponse

Response model for rule execution (reused from existing API).

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `total_points` | `float` | Sum of weighted rule points |
| `pattern_result` | `string` | Concatenated action results from matched rules |
| `action_recommendation` | `string` | Recommended action based on pattern (optional) |
| `rule_evaluations` | `List[RuleEvaluationResult]` | Detailed rule evaluations (dry_run mode only) |
| `would_match` | `List[RuleEvaluationResult]` | Rules that matched (dry_run mode only) |
| `would_not_match` | `List[RuleEvaluationResult]` | Rules that didn't match (dry_run mode only) |
| `dry_run` | `boolean` | Whether this was a dry run |
| `execution_time_ms` | `float` | Total execution time in milliseconds |
| `correlation_id` | `string` | Correlation ID for tracing |

**Example Response**:

```json
{
  "total_points": 10.0,
  "pattern_result": "Spareribs",
  "action_recommendation": null,
  "dry_run": false,
  "execution_time_ms": 45.2,
  "correlation_id": "req-12345"
}
```

**Example Response (Dry Run)**:

```json
{
  "total_points": 10.0,
  "pattern_result": "Spareribs",
  "action_recommendation": null,
  "rule_evaluations": [
    {
      "rule_name": "Dish Decision - Rule 1",
      "rule_priority": 1,
      "condition": "season == \"Fall\"",
      "matched": true,
      "action_result": "Spareribs",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 2.5
    },
    {
      "rule_name": "Dish Decision - Rule 2",
      "rule_priority": 2,
      "condition": "season == \"Winter\"",
      "matched": false,
      "action_result": "-",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 1.8
    }
  ],
  "would_match": [
    {
      "rule_name": "Dish Decision - Rule 1",
      "rule_priority": 1,
      "condition": "season == \"Fall\"",
      "matched": true,
      "action_result": "Spareribs",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 2.5
    }
  ],
  "would_not_match": [
    {
      "rule_name": "Dish Decision - Rule 2",
      "rule_priority": 2,
      "condition": "season == \"Winter\"",
      "matched": false,
      "action_result": "-",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 1.8
    }
  ],
  "dry_run": true,
  "execution_time_ms": 45.2,
  "correlation_id": "req-12345"
}
```

---

## DMN File Format

### Supported DMN Structure

The API supports DMN 1.3 (20191111) format with the following structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="https://www.omg.org/spec/DMN/20191111/MODEL/" 
                 xmlns:feel="https://www.omg.org/spec/DMN/20191111/FEEL/" 
                 id="sample-rules" 
                 name="Sample Rules">
  
  <dmn:decision id="DecisionId" name="Decision Name">
    <dmn:decisionTable id="TableId" hitPolicy="UNIQUE">
      <!-- Input columns -->
      <dmn:input id="InputId" label="Input Label">
        <dmn:inputExpression id="ExprId" typeRef="string">
          <feel:text>attribute_name</feel:text>
        </dmn:inputExpression>
      </dmn:input>
      
      <!-- Output columns -->
      <dmn:output id="OutputId" label="Output Label" typeRef="string"/>
      
      <!-- Rules -->
      <dmn:rule id="RuleId">
        <dmn:inputEntry id="EntryId">
          <feel:text>"value"</feel:text>
        </dmn:inputEntry>
        <dmn:outputEntry id="OutId">
          <feel:text>"result"</feel:text>
        </dmn:outputEntry>
      </dmn:rule>
    </dmn:decisionTable>
  </dmn:decision>
  
</dmn:definitions>
```

### Supported FEEL Expressions

The DMN parser supports the following FEEL expression patterns:

| FEEL Expression | Condition Operator | Example |
|----------------|-------------------|---------|
| `"value"` | `equal` | `"Fall"` → `season == "Fall"` |
| `> 10` | `greater_than` | `> 8` → `guests > 8` |
| `>= 5` | `greater_than_or_equal` | `>= 5` → `guests >= 5` |
| `< 20` | `less_than` | `< 10` → `guests < 10` |
| `<= 15` | `less_than_or_equal` | `<= 8` → `guests <= 8` |
| `[5..10]` | `range` | `[5..8]` → `guests in [5, 8]` |
| `-` | `equal` (matches any) | `-` → matches any value |

### Rule Conversion

DMN rules are converted to the internal rule format as follows:

**DMN Rule Fields**:
- `id`: Rule ID (e.g., `DishDecision_R0001`)
- `rule_name`: Rule name (e.g., `Dish Decision - Rule 1`)
- `attribute`: Input column label (e.g., `Season`)
- `condition`: Condition operator (e.g., `equal`, `less_than`)
- `constant`: Constant value (e.g., `"Fall"`, `8`)
- `action_result`: Output value (e.g., `"Spareribs"`)
- `weight`: Default `1.0`
- `rule_point`: Default `10.0`
- `priority`: Rule index (1-based)

**Execution Format**:
- `rule_name`: Same as DMN rule name
- `condition`: Compiled condition string (e.g., `season == "Fall"`)
- `action_result`: Same as DMN output
- `rule_point`: From DMN rule (default `10.0`)
- `weight`: From DMN rule (default `1.0`)
- `priority`: From DMN rule index

---

## Rule Execution Flow

### Execution Process

1. **Request Validation**
   - Validate that exactly one DMN source is provided (`dmn_file`, `dmn_content`, or `file`)
   - Validate input data is a dictionary
   - Validate optional parameters (`dry_run`, `correlation_id`)

2. **DMN Parsing**
   - If `dmn_file`: Read file from filesystem
   - If `dmn_content`: Parse XML string directly
   - If `file` (upload): Read uploaded file content
   - Parse DMN XML using `DMNParser`
   - Extract decision tables and rules

3. **Rule Conversion**
   - Convert DMN rules to execution format
   - Build condition strings from FEEL expressions
   - Map DMN rule fields to execution format
   - Sort rules by priority

4. **Rule Execution**
   - Iterate through converted rules
   - Evaluate each rule against input data using `rule_run()`
   - Accumulate points: `total_points += rule_point * weight`
   - Build pattern result: concatenate action results
   - Track rule evaluations (if `dry_run=true`)

5. **Action Recommendation** (Optional)
   - Look up action recommendation from patterns dictionary
   - If no patterns provided, skip action recommendation

6. **Response Building**
   - Build `RuleExecutionResponse` with results
   - Include execution metadata (time, correlation_id)
   - Include detailed evaluations if `dry_run=true`

### Execution Logic

```python
# Pseudo-code
def dmn_rules_exec(dmn_source, data, dry_run=False):
    # Parse DMN
    parser = DMNParser()
    if dmn_file:
        result = parser.parse_file(dmn_file)
    elif dmn_content:
        result = parser.parse_content(dmn_content)
    
    rules_set = result['rules_set']
    
    # Convert rules to execution format
    prepared_rules = []
    for dmn_rule in rules_set:
        condition_str = build_condition_string(
            dmn_rule['attribute'],
            dmn_rule['condition'],
            dmn_rule['constant']
        )
        prepared_rule = {
            'rule_name': dmn_rule['rule_name'],
            'condition': condition_str,
            'action_result': dmn_rule['action_result'],
            'rule_point': dmn_rule.get('rule_point', 10.0),
            'weight': dmn_rule.get('weight', 1.0),
            'priority': dmn_rule.get('priority', 1)
        }
        prepared_rules.append(prepared_rule)
    
    # Sort by priority
    prepared_rules.sort(key=lambda r: r['priority'])
    
    # Execute rules
    total_points = 0.0
    pattern_result = ""
    rule_evaluations = []
    
    for rule in prepared_rules:
        eval_result = rule_run(rule, data)
        if eval_result['action_result'] != '-':
            total_points += eval_result['rule_point'] * eval_result['weight']
            pattern_result += eval_result['action_result']
        
        if dry_run:
            rule_evaluations.append({
                'rule_name': rule['rule_name'],
                'matched': eval_result['action_result'] != '-',
                'action_result': eval_result['action_result'],
                ...
            })
    
    # Build response
    return {
        'total_points': total_points,
        'pattern_result': pattern_result,
        'action_recommendation': None,  # Optional
        'rule_evaluations': rule_evaluations if dry_run else None,
        ...
    }
```

---

## Error Handling

### Error Response Format

All errors follow the standard `ErrorResponse` format:

```json
{
  "error_type": "ErrorClassName",
  "message": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "context": {
    "additional": "context"
  },
  "correlation_id": "req-12345"
}
```

### Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `MISSING_DMN_SOURCE` | 400 | Neither dmn_file, dmn_content, nor file provided |
| `MULTIPLE_DMN_SOURCES` | 400 | Multiple DMN sources provided |
| `INVALID_FILE_TYPE` | 400 | File does not have .dmn extension |
| `DMN_PARSE_ERROR` | 400 | Invalid DMN XML format |
| `DMN_READ_ERROR` | 400 | Failed to read DMN file |
| `DATA_INVALID_TYPE` | 400 | Input data is not a dictionary |
| `DATA_NONE` | 400 | Input data is None |
| `RULE_EVALUATION_ERROR` | 500 | Error during rule execution |
| `CONFIGURATION_ERROR` | 500 | Configuration error |

### Error Examples

**Missing DMN Source**:
```json
{
  "error_type": "DataValidationError",
  "message": "Exactly one of dmn_file, dmn_content, or file must be provided",
  "error_code": "MISSING_DMN_SOURCE",
  "correlation_id": "req-12345"
}
```

**Invalid DMN Format**:
```json
{
  "error_type": "ConfigurationError",
  "message": "Invalid DMN XML format: ...",
  "error_code": "DMN_PARSE_ERROR",
  "context": {
    "file_path": "data/input/invalid.dmn",
    "error": "XML parsing error details"
  },
  "correlation_id": "req-12345"
}
```

**Invalid Input Data**:
```json
{
  "error_type": "DataValidationError",
  "message": "Input data must be a dictionary, got str",
  "error_code": "DATA_INVALID_TYPE",
  "context": {
    "data_type": "str"
  },
  "correlation_id": "req-12345"
}
```

---

## Examples

### Example 1: Execute Rules from File Path

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/rules/execute-dmn" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "dmn_file": "data/input/sample_rules.dmn",
    "data": {
      "season": "Fall",
      "guests": 6
    },
    "dry_run": false,
    "correlation_id": "req-001"
  }'
```

**Response**:
```json
{
  "total_points": 10.0,
  "pattern_result": "Spareribs",
  "action_recommendation": null,
  "dry_run": false,
  "execution_time_ms": 42.5,
  "correlation_id": "req-001"
}
```

---

### Example 2: Execute Rules from XML Content

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/rules/execute-dmn" \
  -H "Content-Type: application/json" \
  -d '{
    "dmn_content": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><dmn:definitions xmlns:dmn=\"https://www.omg.org/spec/DMN/20191111/MODEL/\"><dmn:decision id=\"DishDecision\"><dmn:decisionTable><dmn:input id=\"SeasonInput\" label=\"Season\"><dmn:inputExpression><feel:text>season</feel:text></dmn:inputExpression></dmn:input><dmn:output id=\"DishOutput\" label=\"Dish\"/><dmn:rule id=\"Rule1\"><dmn:inputEntry><feel:text>\"Winter\"</feel:text></dmn:inputEntry><dmn:outputEntry><feel:text>\"Roastbeef\"</feel:text></dmn:outputEntry></dmn:rule></dmn:decisionTable></dmn:decision></dmn:definitions>",
    "data": {
      "season": "Winter",
      "guests": 5
    }
  }'
```

**Response**:
```json
{
  "total_points": 10.0,
  "pattern_result": "Roastbeef",
  "action_recommendation": null,
  "dry_run": false,
  "execution_time_ms": 38.2,
  "correlation_id": null
}
```

---

### Example 3: Execute Rules with File Upload

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/rules/execute-dmn-upload" \
  -H "X-API-Key: your-api-key" \
  -F "file=@sample_rules.dmn" \
  -F "data={\"season\": \"Spring\", \"guests\": 7}" \
  -F "dry_run=false" \
  -F "correlation_id=req-002"
```

**Response**:
```json
{
  "total_points": 10.0,
  "pattern_result": "Steak",
  "action_recommendation": null,
  "dry_run": false,
  "execution_time_ms": 45.8,
  "correlation_id": "req-002"
}
```

---

### Example 4: Dry Run Mode

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/rules/execute-dmn" \
  -H "Content-Type: application/json" \
  -d '{
    "dmn_file": "data/input/sample_rules.dmn",
    "data": {
      "season": "Fall",
      "guests": 6
    },
    "dry_run": true
  }'
```

**Response**:
```json
{
  "total_points": 10.0,
  "pattern_result": "Spareribs",
  "action_recommendation": null,
  "rule_evaluations": [
    {
      "rule_name": "Dish Decision - Rule 1",
      "rule_priority": 1,
      "condition": "season == \"Fall\"",
      "matched": true,
      "action_result": "Spareribs",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 2.1
    },
    {
      "rule_name": "Dish Decision - Rule 2",
      "rule_priority": 2,
      "condition": "season == \"Winter\"",
      "matched": false,
      "action_result": "-",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 1.9
    },
    {
      "rule_name": "Dish Decision - Rule 3",
      "rule_priority": 3,
      "condition": "season == \"Spring\"",
      "matched": false,
      "action_result": "-",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 1.8
    }
  ],
  "would_match": [
    {
      "rule_name": "Dish Decision - Rule 1",
      "rule_priority": 1,
      "condition": "season == \"Fall\"",
      "matched": true,
      "action_result": "Spareribs",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 2.1
    }
  ],
  "would_not_match": [
    {
      "rule_name": "Dish Decision - Rule 2",
      "rule_priority": 2,
      "condition": "season == \"Winter\"",
      "matched": false,
      "action_result": "-",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 1.9
    },
    {
      "rule_name": "Dish Decision - Rule 3",
      "rule_priority": 3,
      "condition": "season == \"Spring\"",
      "matched": false,
      "action_result": "-",
      "rule_point": 10.0,
      "weight": 1.0,
      "execution_time_ms": 1.8
    }
  ],
  "dry_run": true,
  "execution_time_ms": 48.5,
  "correlation_id": null
}
```

---

## Limitations

### Current Limitations

1. **Single Input/Output Column**: Currently, only the first input and first output columns from DMN decision tables are used. Multi-column support may be added in future versions.

2. **Hit Policy**: All hit policies are supported during parsing, but the execution doesn't differentiate between them. All matching rules are executed and results are concatenated.

3. **FEEL Expression Support**: Limited FEEL expression support. Complex expressions may not be fully parsed. Supported patterns:
   - String literals: `"value"`
   - Numeric comparisons: `>`, `>=`, `<`, `<=`
   - Ranges: `[a..b]`
   - Wildcard: `-`

4. **Action Recommendations**: Action recommendations are optional and require a patterns dictionary. DMN files don't include patterns, so action recommendations will be `null` unless patterns are provided separately.

5. **Rule Points and Weights**: Default values (`rule_point: 10.0`, `weight: 1.0`) are used if not specified in DMN. DMN standard doesn't include these fields, so they're set to defaults.

6. **Complex Rules**: Only simple rules (single condition) are fully supported. Complex rules with multiple conditions and logical operators may require additional configuration.

### Future Enhancements

- Support for multiple input/output columns
- Enhanced FEEL expression parsing
- Support for DMN hit policies (FIRST, COLLECT, etc.)
- Support for complex rules with multiple conditions
- Custom rule points and weights in DMN
- Pattern matching for action recommendations
- Caching of parsed DMN files

---

## Integration with Existing API

### Relationship to `/api/v1/rules/execute`

The DMN execution endpoint (`/execute-dmn`) complements the existing rule execution endpoint (`/execute`) by:

- **Flexibility**: Execute rules without pre-configuration
- **Ad-hoc Testing**: Test DMN files before adding them to configuration
- **Temporary Rules**: Execute rules that don't need to be persisted
- **Migration**: Test DMN files before migrating to JSON configuration

### Differences

| Feature | `/execute` | `/execute-dmn` |
|---------|-----------|----------------|
| Rule Source | Pre-configured (JSON/DMN) | On-demand (DMN only) |
| Configuration | Required | Not required |
| Caching | Yes (via ConfigLoader) | No (parsed on each request) |
| Performance | Faster (cached) | Slower (parsing overhead) |
| Use Case | Production rules | Testing, ad-hoc execution |

---

## Security Considerations

1. **File Path Validation**: Validate file paths to prevent directory traversal attacks
2. **File Size Limits**: Enforce maximum file size for uploaded DMN files
3. **XML Parsing**: Use safe XML parsing to prevent XXE attacks
4. **Input Validation**: Validate all input data before execution
5. **Rate Limiting**: Consider rate limiting for DMN execution endpoints

---

## Performance Considerations

1. **Parsing Overhead**: DMN parsing adds overhead compared to pre-configured rules
2. **File I/O**: File-based execution requires file system access
3. **Caching**: Consider caching parsed DMN files for frequently used files
4. **Large Files**: Large DMN files may impact performance

---

## Version History

- **v1.0.0** (Initial): Basic DMN execution support
  - File path and content-based execution
  - File upload support
  - Dry run mode
  - Basic FEEL expression support

---

## References

- [DMN Specification](https://www.omg.org/spec/DMN/)
- [FEEL Specification](https://www.omg.org/spec/DMN/)
- [API Documentation](./API_DOCUMENTATION.md)
- [DMN Parser Feature](./DMN_PARSER_FEATURE.md)
