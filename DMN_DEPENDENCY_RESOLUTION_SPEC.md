# DMN Decision Dependency Resolution - Technical Specification

## Overview

This specification defines the implementation of DMN decision dependency resolution to fix `SymbolResolutionError` issues when executing dependent decisions. The feature enables proper execution order and output mapping for DMN decisions that depend on other decisions.

## Problem Statement

When executing DMN files with decision dependencies (via `InformationRequirement`), dependent decisions fail because:
- Rules reference fields (e.g., `element_1`, `element_2`) that come from dependent decisions
- Dependent decisions are not executed first
- Outputs from dependent decisions are not mapped to input field names
- Data dictionary lacks required fields when evaluating dependent rules

**Example Error**:
```
SymbolResolutionError: element_1
```

## Solution Architecture

### High-Level Flow

```
1. Parse DMN → Extract decisions + dependencies
2. Build dependency graph → Topological sort
3. Execute in order:
   a. Independent decisions (Can, Chi)
   b. Collect outputs → Map to field names
   c. Enrich data dictionary
   d. Dependent decisions (Ngu Hanh)
4. Return aggregated results
```

## Data Structures

### Decision Metadata

```python
DecisionMetadata = {
    "decision_id": str,              # e.g., "Decision_0n3v7en"
    "decision_name": str,             # e.g., "Ngu Hanh"
    "dependencies": List[str],        # e.g., ["Decision_0nq1td4", "Decision_0kgjdku"]
    "rules": List[Dict],               # Parsed rules from decision table
    "inputs": List[Dict],              # Input column definitions
    "outputs": List[Dict],             # Output column definitions with labels
    "output_field_mapping": Dict[str, str]  # {output_label: input_field_name}
}
```

### Output Mapping

```python
OutputMapping = {
    "decision_id": str,
    "outputs": {
        "output_label": "output_value"  # e.g., {"element_1": "wood", "element_2": "water"}
    }
}
```

### Execution Context

```python
ExecutionContext = {
    "data": Dict[str, Any],           # Original + enriched data
    "decision_outputs": Dict[str, Dict[str, Any]],  # {decision_id: {field: value}}
    "execution_order": List[str],      # Ordered decision IDs
    "executed_decisions": Set[str]     # Track completed decisions
}
```

## API Changes

### DMNParser Class

#### New Methods

**`_parse_information_requirements(decision: Element, namespace: Dict[str, str]) -> List[str]`**

Extracts dependent decision IDs from `InformationRequirement` elements.

**Parameters**:
- `decision`: XML decision element
- `namespace`: DMN namespace mapping

**Returns**:
- List of dependent decision IDs (e.g., `["Decision_0nq1td4", "Decision_0kgjdku"]`)

**Algorithm**:
1. Find all `<informationRequirement>` elements within decision
2. Extract `href` from `<requiredDecision>` elements
3. Remove `#` prefix from hrefs
4. Return list of decision IDs

**Example**:
```xml
<informationRequirement id="InfoReq_1">
  <requiredDecision href="#Decision_0nq1td4" />
</informationRequirement>
```
→ Returns: `["Decision_0nq1td4"]`

---

**`_build_execution_order(decisions_metadata: List[DecisionMetadata]) -> List[str]`**

Builds dependency graph and returns topological sort order.

**Parameters**:
- `decisions_metadata`: List of decision metadata with dependencies

**Returns**:
- Ordered list of decision IDs (independent first, dependent last)

**Algorithm** (Topological Sort):
1. Build graph: `{decision_id: set(dependent_ids)}`
2. Calculate in-degrees for each node
3. Start with nodes having in-degree = 0 (independent)
4. Process nodes, decrementing dependent nodes' in-degrees
5. Add to result when in-degree reaches 0
6. Detect cycles (if remaining nodes have in-degree > 0)

**Edge Cases**:
- Circular dependencies → Log warning, return original order
- Missing dependencies → Log warning, treat as independent
- No dependencies → Return all decisions in original order

---

**`_get_output_field_mapping(outputs: List[Dict], decision_id: str) -> Dict[str, str]`**

Maps output labels to input field names for dependent decisions.

**Parameters**:
- `outputs`: List of output column definitions
- `decision_id`: Decision ID for logging

**Returns**:
- Dictionary mapping output labels to field names: `{output_label: field_name}`

**Algorithm**:
1. Extract `label` or `name` from each output
2. Use label as both output identifier and input field name
3. Return mapping dictionary

**Example**:
```python
outputs = [
    {"id": "Output_1", "label": "element_1", "type": "string"},
    {"id": "Output_2", "label": "element_2", "type": "string"}
]
```
→ Returns: `{"element_1": "element_1", "element_2": "element_2"}`

---

#### Modified Methods

**`parse_file(file_path: str) -> Dict[str, Any]`**

**Changes**:
- Extract `InformationRequirement` dependencies for each decision
- Build execution order using dependency graph
- Return additional metadata:
  ```python
  {
      "rules_set": List[Dict],
      "patterns": Dict,
      "decisions_metadata": List[DecisionMetadata],
      "execution_order": List[str]
  }
  ```

**`parse_content(xml_content: str) -> Dict[str, Any]`**

Same changes as `parse_file()`.

**`_parse_decision_table(decision: Element, namespace: Dict[str, str]) -> Tuple[List[Dict], DecisionMetadata]`**

**Changes**:
- Extract dependencies using `_parse_information_requirements()`
- Extract output field mappings
- Return tuple: `(rules, metadata)` instead of just `rules`

**`_parse_outputs(decision_table: Element, ns_uri: str) -> List[Dict[str, Any]]`**

**Changes**:
- Extract `label` and `name` attributes from output elements
- Store in output dictionary: `{"id": ..., "label": ..., "name": ..., "type": ...}`

### ruleengine_exec Module

#### Modified Functions

**`dmn_rules_exec(...) -> Dict[str, Any]`**

**Changes**:
1. After parsing DMN, extract `decisions_metadata` and `execution_order`
2. Group rules by `decision_id`
3. Execute decisions in topological order:
   ```python
   for decision_id in execution_order:
       # Execute decision's rules
       decision_outputs = execute_decision_rules(decision_id, data)
       # Map outputs to field names
       mapped_outputs = map_decision_outputs(decision_id, decision_outputs)
       # Enrich data dictionary
       data.update(mapped_outputs)
   ```
4. Aggregate results from all decisions

#### New Helper Functions

**`_execute_decision_rules(decision_id: str, rules: List[Dict], data: Dict[str, Any], dry_run: bool) -> Dict[str, Any]`**

Executes all rules for a single decision and collects outputs.

**Parameters**:
- `decision_id`: Decision identifier
- `rules`: List of prepared rules for this decision
- `data`: Current data dictionary
- `dry_run`: Dry run flag

**Returns**:
- Dictionary with:
  - `matched_outputs`: List of action_result values from matched rules
  - `all_outputs`: List of all output values (for hit policy handling)
  - `executed_count`: Number of rules executed
  - `matched_count`: Number of rules matched

**Algorithm**:
1. Execute each rule using `rule_run(rule, data)`
2. Collect `action_result` from matched rules
3. Handle hit policies:
   - `UNIQUE`: Return first matched output
   - `FIRST`: Return first matched output
   - `COLLECT`: Return all matched outputs (as list)
   - `ANY`: Return any matched output
4. Return collected outputs

---

**`_map_decision_outputs(decision_metadata: DecisionMetadata, execution_result: Dict[str, Any]) -> Dict[str, Any]`**

Maps decision outputs to input field names.

**Parameters**:
- `decision_metadata`: Decision metadata with output mappings
- `execution_result`: Execution result from `_execute_decision_rules()`

**Returns**:
- Dictionary mapping field names to output values: `{field_name: output_value}`

**Algorithm**:
1. Get output field mapping from metadata
2. Extract matched outputs from execution result
3. Map outputs to field names:
   - Single output: `{output_label: matched_output}`
   - Multiple outputs: Handle based on output structure
4. Return mapped dictionary

**Example**:
```python
metadata = {
    "output_field_mapping": {"element_1": "element_1"},
    "outputs": [{"label": "element_1"}]
}
execution_result = {"matched_outputs": ["wood"]}
```
→ Returns: `{"element_1": "wood"}`

---

**`_group_rules_by_decision(rules_set: List[Dict], decisions_metadata: List[DecisionMetadata]) -> Dict[str, List[Dict]]`**

Groups rules by their decision ID.

**Parameters**:
- `rules_set`: Flat list of all rules
- `decisions_metadata`: List of decision metadata

**Returns**:
- Dictionary: `{decision_id: [rules_for_decision]}`

**Algorithm**:
1. Extract `decision_id` from each rule (stored in rule metadata)
2. Group rules by decision_id
3. Return grouped dictionary

## Execution Flow

### Detailed Algorithm

```
1. PARSE DMN
   ├─ Parse all decisions
   ├─ Extract InformationRequirement dependencies
   ├─ Build decisions_metadata with dependencies
   └─ Build execution_order (topological sort)

2. GROUP RULES
   └─ Group rules by decision_id

3. EXECUTE DECISIONS (in order)
   For each decision_id in execution_order:
   
   a. GET DECISION RULES
      └─ Retrieve rules for this decision
   
   b. EXECUTE RULES
      ├─ For each rule: rule_run(rule, data)
      ├─ Collect matched outputs
      └─ Handle hit policy
   
   c. MAP OUTPUTS
      ├─ Get output field mapping from metadata
      ├─ Map outputs to input field names
      └─ Return: {field_name: output_value}
   
   d. ENRICH DATA
      └─ data.update(mapped_outputs)
   
   e. CONTINUE
      └─ Proceed to next decision

4. AGGREGATE RESULTS
   ├─ Combine total_points from all decisions
   ├─ Combine pattern_result from all decisions
   └─ Return final result
```

## Example Execution

### Input DMN Structure

```xml
<decision id="Decision_0nq1td4" name="Can">
  <decisionTable>
    <input label="can" />
    <output label="element_1" />
    <!-- rules -->
  </decisionTable>
</decision>

<decision id="Decision_0kgjdku" name="Chi">
  <decisionTable>
    <input label="chi" />
    <output label="element_2" />
    <!-- rules -->
  </decisionTable>
</decision>

<decision id="Decision_0n3v7en" name="Ngu Hanh">
  <informationRequirement>
    <requiredDecision href="#Decision_0nq1td4" />
  </informationRequirement>
  <informationRequirement>
    <requiredDecision href="#Decision_0kgjdku" />
  </informationRequirement>
  <decisionTable>
    <input label="element_1" />
    <input label="element_2" />
    <output label="element_score" />
    <!-- rules -->
  </decisionTable>
</decision>
```

### Input Data

```python
data = {
    "can": "giap",
    "chi": "ty"
}
```

### Execution Steps

**Step 1: Parse and Build Order**
```python
execution_order = ["Decision_0nq1td4", "Decision_0kgjdku", "Decision_0n3v7en"]
```

**Step 2: Execute Decision_0nq1td4 (Can)**
```python
# Execute rules with data={"can": "giap"}
matched_output = "wood"  # From matched rule
mapped_outputs = {"element_1": "wood"}
data.update(mapped_outputs)
# data = {"can": "giap", "chi": "ty", "element_1": "wood"}
```

**Step 3: Execute Decision_0kgjdku (Chi)**
```python
# Execute rules with data={"can": "giap", "chi": "ty", "element_1": "wood"}
matched_output = "water"  # From matched rule
mapped_outputs = {"element_2": "water"}
data.update(mapped_outputs)
# data = {"can": "giap", "chi": "ty", "element_1": "wood", "element_2": "water"}
```

**Step 4: Execute Decision_0n3v7en (Ngu Hanh)**
```python
# Execute rules with enriched data
# Rules can now access element_1="wood" and element_2="water"
# No SymbolResolutionError!
```

## Error Handling

### Circular Dependencies

**Detection**: After topological sort, if nodes remain with in-degree > 0

**Handling**:
- Log warning with cycle details
- Use original decision order
- Continue execution

**Log Message**:
```
WARNING: Circular dependency detected in decisions: [Decision_A, Decision_B, Decision_C]. Using original order.
```

### Missing Dependent Decision

**Detection**: Required decision ID not found in parsed decisions

**Handling**:
- Log warning
- Treat as independent decision
- Continue execution

**Log Message**:
```
WARNING: Dependent decision 'Decision_X' not found. Treating as independent.
```

### Missing Output Mapping

**Detection**: Decision has no outputs or output labels

**Handling**:
- Log warning
- Skip output mapping
- Continue with next decision

**Log Message**:
```
WARNING: Decision 'Decision_X' has no outputs. Skipping output mapping.
```

### No Matched Rules

**Detection**: Decision execution returns no matched outputs

**Handling**:
- Log info message
- Skip output mapping (no outputs to map)
- Continue with next decision

**Log Message**:
```
INFO: Decision 'Decision_X' matched no rules. No outputs to map.
```

## Hit Policy Handling

### UNIQUE / FIRST
- Return first matched output value
- Map to single field name

### COLLECT
- Return list of all matched outputs
- Map to field name as list (or handle based on output structure)

### ANY
- Return any matched output
- Map to single field name

### Priority
- Rules already sorted by priority
- First matched rule's output is used

## Logging

### Dependency Resolution Logs

**Level**: INFO
```
INFO: Parsed DMN dependencies: Decision_0n3v7en depends on [Decision_0nq1td4, Decision_0kgjdku]
INFO: Execution order: [Decision_0nq1td4, Decision_0kgjdku, Decision_0n3v7en]
```

**Level**: DEBUG
```
DEBUG: Executing decision Decision_0nq1td4 (independent)
DEBUG: Decision Decision_0nq1td4 matched 1 rule(s), output: wood
DEBUG: Mapped outputs: {'element_1': 'wood'}
DEBUG: Enriched data with dependent outputs: {'element_1': 'wood'}
```

**Level**: WARNING
```
WARNING: Circular dependency detected: [Decision_A, Decision_B]
WARNING: Missing dependent decision: Decision_X
WARNING: Decision Decision_X has no outputs
```

## Testing Requirements

### Unit Tests

1. **Dependency Parsing**
   - Parse InformationRequirement elements
   - Extract requiredDecision hrefs
   - Handle missing dependencies

2. **Topological Sort**
   - Simple chain: A → B → C
   - Multiple dependencies: C depends on [A, B]
   - Circular dependency detection
   - Independent decisions

3. **Output Mapping**
   - Single output mapping
   - Multiple outputs mapping
   - Missing output labels

4. **Execution Order**
   - Independent decisions execute first
   - Dependent decisions execute after
   - Data enrichment between executions

### Integration Tests

1. **End-to-End Execution**
   - Execute DMN file with dependencies
   - Verify execution order
   - Verify output mapping
   - Verify data enrichment
   - Verify no SymbolResolutionError

2. **Edge Cases**
   - DMN with no dependencies
   - DMN with circular dependencies
   - DMN with missing dependent decisions
   - DMN with decisions having no outputs

### Test Data

Use existing DMN file: `data/input/Tương Sinh Tương Khắc.dmn`

**Test Case 1**: Basic dependency resolution
```python
data = {"can": "giap", "chi": "ty"}
# Expected: element_1="wood", element_2="water", Ngu Hanh rules execute successfully
```

**Test Case 2**: Multiple dependencies
```python
data = {"can": "at", "chi": "suu"}
# Expected: element_1="wood", element_2="earth", Ngu Hanh rules execute
```

## Performance Considerations

### Optimization

1. **Caching**: Cache parsed dependency graph
2. **Lazy Evaluation**: Only execute decisions when needed
3. **Early Termination**: Skip dependent decisions if independent ones fail

### Complexity

- **Dependency Parsing**: O(n) where n = number of decisions
- **Topological Sort**: O(V + E) where V = decisions, E = dependencies
- **Execution**: O(R) where R = total rules across all decisions

## Backward Compatibility

### Existing Behavior

- DMN files without dependencies continue to work
- Execution order remains same for independent decisions
- API signatures unchanged (internal implementation change)

### Breaking Changes

None - this is an internal enhancement.

## Migration Notes

### For Users

No changes required. Existing DMN files with dependencies will automatically benefit from dependency resolution.

### For Developers

- New internal data structures (`DecisionMetadata`, `ExecutionContext`)
- New helper methods in `DMNParser` and `ruleengine_exec`
- Enhanced logging for dependency resolution

## Future Enhancements

1. **Output Transformation**: Support FEEL expressions in output mapping
2. **Conditional Dependencies**: Support conditional execution based on data
3. **Parallel Execution**: Execute independent decisions in parallel
4. **Dependency Visualization**: Generate dependency graph diagrams

## References

- DMN 1.3 Specification: InformationRequirement
- Topological Sort Algorithm
- DMN Hit Policies
