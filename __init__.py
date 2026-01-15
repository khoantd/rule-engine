"""
Rule Engine Package.

A flexible and extensible rule engine for evaluating business rules and workflows.

This package provides:
- Rule evaluation and execution
- Workflow management
- Configuration management
- AWS Lambda integration
- JSON utilities
- Domain models

Main Entry Points:
- AWS Lambda: aws_main_rule_exec.lambda_handler
- Rule Execution: services.ruleengine_exec.rules_exec
- Workflow Execution: services.workflow_exec.wf_exec
"""

# Version information
__version__ = '1.0.0'
__author__ = 'Rule Engine Team'

# Public API
from services.ruleengine_exec import rules_exec
from services.workflow_exec import wf_exec

__all__ = [
    '__version__',
    '__author__',
    'rules_exec',
    'wf_exec',
]

