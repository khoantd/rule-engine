# DMN Parser Feature

## Overview

This feature adds support for parsing Decision Model Notation (DMN) XML files and converting them to the rule engine's internal rule format. DMN is a standard notation for decision modeling that uses decision tables to define business rules.

## Implementation

### Components

1. **DMN Parser Module** (`common/dmn_parser.py`)
   - `DMNParser` class that parses DMN XML files
   - Converts DMN decision tables to rule format
   - Supports FEEL (Friendly Enough Expression Language) expressions

2. **Repository Integration** (`common/repository/config_repository.py`)
   - `FileConfigRepository` now automatically detects `.dmn` files
   - Parses DMN files and converts them to JSON format
   - Seamlessly integrates with existing rule loading infrastructure

3. **Sample DMN File** (`data/input/sample_rules.dmn`)
   - Example DMN file demonstrating the format
   - Can be used as a reference for creating DMN rule files

### Features

- **DMN XML Parsing**: Parses standard DMN XML files
- **Decision Table Extraction**: Extracts decision tables from DMN files
- **FEEL Expression Parsing**: Parses FEEL expressions to extract conditions:
  - Comparison operators: `>`, `>=`, `<`, `<=`
  - Equality: `=`, `==`
  - Ranges: `[a..b]`
  - Lists: `[a, b, c]`
  - String literals: `"value"`
- **Rule Conversion**: Converts DMN rules to internal rule format with:
  - Rule ID (based on decision ID and rule index)
  - Rule name (based on decision name)
  - Attribute (from input column label)
  - Condition (parsed from FEEL expression)
  - Constant (extracted from FEEL expression)
  - Action result (from output column)
  - Priority (based on rule order)
  - Default weight and rule points

### Usage

#### Using DMN Files Directly

```python
from common.dmn_parser import DMNParser

parser = DMNParser()
result = parser.parse_file('data/input/sample_rules.dmn')
rules = result['rules_set']
```

#### Using with ConfigRepository

The DMN parser is automatically integrated with the configuration repository:

```python
from common.repository.config_repository import FileConfigRepository

repository = FileConfigRepository()
rules = repository.read_rules_set('data/input/sample_rules.dmn')
```

#### Using with RuleManagementService

The `RuleManagementService` automatically supports DMN files:

```python
from services.rule_management import RuleManagementService

service = RuleManagementService()
# If config points to a .dmn file, it will be parsed automatically
rules = service.list_rules()
```

### DMN File Format

DMN files are XML-based. A basic structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="https://www.omg.org/spec/DMN/20191111/MODEL/" 
                 id="my-rules" name="My Rules">
  <dmn:decision id="Decision1" name="My Decision">
    <dmn:decisionTable id="Table1" hitPolicy="UNIQUE">
      <dmn:input id="Input1" label="Value">
        <dmn:inputExpression id="Expr1" typeRef="number">
          <feel:text>value</feel:text>
        </dmn:inputExpression>
      </dmn:input>
      <dmn:output id="Output1" label="Result" typeRef="string"/>
      <dmn:rule id="Rule1">
        <dmn:inputEntry id="Entry1">
          <feel:text>&gt; 10</feel:text>
        </dmn:inputEntry>
        <dmn:outputEntry id="Out1">
          <feel:text>"Approved"</feel:text>
        </dmn:outputEntry>
      </dmn:rule>
    </dmn:decisionTable>
  </dmn:decision>
</dmn:definitions>
```

### Supported FEEL Expressions

| FEEL Expression | Condition | Constant |
|----------------|-----------|----------|
| `> 10` | `greater_than` | `10` |
| `>= 5` | `greater_than_or_equal` | `5` |
| `< 20` | `less_than` | `20` |
| `<= 15` | `less_than_or_equal` | `15` |
| `"value"` | `equal` | `"value"` |
| `[5..10]` | `range` | `[5, 10]` |
| `-` | `equal` | `''` (matches anything) |

### Limitations

1. **Single Input/Output**: Currently, only the first input and first output columns are used. Multi-column support can be added in the future.

2. **Hit Policy**: All hit policies are supported, but the conversion doesn't differentiate between them (all rules are converted).

3. **Complex FEEL Expressions**: Advanced FEEL expressions (functions, context, etc.) are not fully supported. Basic comparison and range expressions are supported.

4. **Patterns**: DMN files don't contain patterns, so the `patterns` field is always empty in the converted output.

### Testing

Unit tests are available in `tests/unit/test_dmn_parser.py`:

```bash
pytest tests/unit/test_dmn_parser.py -v
```

### References

- [DMN Specification](https://www.omg.org/dmn/)
- [FEEL Language Specification](https://www.omg.org/spec/DMN/1.3/PDF)
- [dmn-check Tool](https://github.com/red6/dmn-check) - Reference implementation for DMN validation

### Future Enhancements

1. Support for multiple input/output columns
2. Better FEEL expression parsing (functions, context, etc.)
3. Support for DMN decision requirement graphs (DRG)
4. Validation of DMN files against DMN schema
5. Support for DMN 1.4 and later versions
