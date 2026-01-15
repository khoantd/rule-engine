"""
Common utilities and helper functions for Rule Engine.

This module provides:
- Rule engine utilities
- JSON utilities
- Configuration utilities
- S3/AWS utilities
- Exception classes
- Logging utilities
"""

from common.exceptions import (
    RuleEngineException,
    ConfigurationError,
    RuleEvaluationError,
    DataValidationError,
    RuleCompilationError,
    ConditionError,
    WorkflowError,
    StorageError,
    ExternalServiceError,
)

from common.json_util import (
    read_json_file,
    create_json_file,
    parse_json,
    parse_json_v2,
    json_to_row_data_convert,
)

from common.rule_engine_util import (
    rules_set_cfg_read,
    actions_set_cfg_read,
    conditions_set_cfg_read,
    rules_set_setup,
    rules_set_exec,
    rule_prepare,
    conditions_set_load,
    rule_setup,
    condition_setup,
    rules_set_read,
    condition_set_read,
    rules_set_from_s3_read,
    rule_actions_read,
    rule_actions_from_S3_read,
    find_action_recommendation,
    rule_run,
    sort_by_priority,
)

from common.util import (
    cfg_read,
)

from common.s3_aws_util import (
    aws_s3_config_file_read,
    config_file_read,
    S3_BUCKET_RULE_CONFIG,
)

from common.config import (
    Config,
    get_config,
    set_config,
)

__all__ = [
    # Exceptions
    'RuleEngineException',
    'ConfigurationError',
    'RuleEvaluationError',
    'DataValidationError',
    'RuleCompilationError',
    'ConditionError',
    'WorkflowError',
    'StorageError',
    'ExternalServiceError',
    # JSON utilities
    'read_json_file',
    'create_json_file',
    'parse_json',
    'parse_json_v2',
    'json_to_row_data_convert',
    # Rule engine utilities
    'rules_set_cfg_read',
    'actions_set_cfg_read',
    'conditions_set_cfg_read',
    'rules_set_setup',
    'rules_set_exec',
    'rule_prepare',
    'conditions_set_load',
    'rule_setup',
    'condition_setup',
    'rules_set_read',
    'condition_set_read',
    'rules_set_from_s3_read',
    'rule_actions_read',
    'rule_actions_from_S3_read',
    'find_action_recommendation',
    'rule_run',
    'sort_by_priority',
    # Configuration utilities
    'cfg_read',
    # S3 utilities
    'aws_s3_config_file_read',
    'config_file_read',
    'S3_BUCKET_RULE_CONFIG',
    # Config class
    'Config',
    'get_config',
    'set_config',
]

