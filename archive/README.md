# Archive Directory

This directory contains deprecated or unused files that have been replaced by newer implementations.

## Deprecated Files

### `main_rule_exec_v1.py` and `main_rule_exec_v2.py`

**Status**: Deprecated
**Replaced By**: `services/ruleengine_exec.py` and `aws_main_rule_exec.py`
**Reason**: These were legacy implementations before the codebase was refactored into a service-based architecture.

**Current Entry Points**:
- **AWS Lambda**: Use `aws_main_rule_exec.py::lambda_handler()`
- **Direct Execution**: Use `services.ruleengine_exec::rules_exec()`
- **Workflow Execution**: Use `services.workflow_exec::wf_exec()`

**Migration Path**:
1. If you were using `main_rule_exec_v1.py` or `main_rule_exec_v2.py`, migrate to:
   ```python
   from services.ruleengine_exec import rules_exec
   result = rules_exec(data)
   ```

2. For AWS Lambda deployments, use `aws_main_rule_exec.py` which provides:
   - Input validation
   - Error handling
   - Logging
   - Structured responses

**Note**: These files are kept for reference and historical purposes. They should not be used in new code.

---

## Archive Guidelines

Files are moved to this directory when:
1. They are replaced by better implementations
2. They are no longer maintained
3. They represent legacy code that is kept for reference
4. Migration path exists and is documented

Before removing files completely, they are archived here for a grace period to ensure no dependencies exist.

