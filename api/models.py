"""
API request and response models for Rule Engine web service.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class RuleExecutionRequest(BaseModel):
    """Request model for rule execution."""
    
    data: Dict[str, Any] = Field(..., description="Input data for rule evaluation")
    dry_run: bool = Field(default=False, description="Execute rules without side effects")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracing")
    
    @validator('data')
    def validate_data(cls, v):
        """Validate that data is a non-empty dictionary."""
        if not isinstance(v, dict):
            raise ValueError("data must be a dictionary")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "issue": 35,
                    "title": "Superman",
                    "publisher": "DC"
                },
                "dry_run": False,
                "correlation_id": "req-12345"
            }
        }


class RuleEvaluationResult(BaseModel):
    """Individual rule evaluation result."""
    
    rule_name: str
    rule_priority: Optional[int] = None
    condition: str
    matched: bool
    action_result: str
    rule_point: float
    weight: float
    execution_time_ms: float


class RuleExecutionResponse(BaseModel):
    """Response model for rule execution."""
    
    total_points: float = Field(..., description="Sum of weighted rule points")
    pattern_result: str = Field(..., description="Concatenated action results")
    action_recommendation: Optional[str] = Field(None, description="Recommended action based on pattern")
    decision_outputs: Optional[Dict[str, Any]] = Field(None, description="Decision outputs from DMN execution (field_name: output_value)")
    rule_evaluations: Optional[List[RuleEvaluationResult]] = Field(None, description="Detailed rule evaluations (dry_run mode)")
    would_match: Optional[List[RuleEvaluationResult]] = Field(None, description="Rules that matched (dry_run mode)")
    would_not_match: Optional[List[RuleEvaluationResult]] = Field(None, description="Rules that didn't match (dry_run mode)")
    dry_run: Optional[bool] = Field(None, description="Whether this was a dry run")
    execution_time_ms: Optional[float] = Field(None, description="Total execution time in milliseconds")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_points": 1050.0,
                "pattern_result": "YYY",
                "action_recommendation": "Approved",
                "correlation_id": "req-12345",
                "execution_time_ms": 45.2
            }
        }


class BatchRuleExecutionRequest(BaseModel):
    """Request model for batch rule execution."""
    
    data_list: List[Dict[str, Any]] = Field(..., description="List of input data dictionaries")
    dry_run: bool = Field(default=False, description="Execute rules without side effects")
    max_workers: Optional[int] = Field(default=None, description="Maximum number of parallel workers")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for batch tracking")
    
    @validator('data_list')
    def validate_data_list(cls, v):
        """Validate that data_list is a non-empty list of dictionaries."""
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("data_list must be a non-empty list")
        for item in v:
            if not isinstance(item, dict):
                raise ValueError("All items in data_list must be dictionaries")
        return v
    
    @validator('max_workers')
    def validate_max_workers(cls, v):
        """Validate max_workers is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("max_workers must be positive")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "data_list": [
                    {"issue": 35, "title": "Superman", "publisher": "DC"},
                    {"issue": 10, "title": "Batman", "publisher": "DC"}
                ],
                "dry_run": False,
                "max_workers": 4,
                "correlation_id": "batch-12345"
            }
        }


class BatchItemResult(BaseModel):
    """Result for a single item in a batch execution."""
    
    item_index: int
    correlation_id: str
    status: str
    total_points: Optional[float] = None
    pattern_result: Optional[str] = None
    action_recommendation: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


class BatchRuleExecutionResponse(BaseModel):
    """Response model for batch rule execution."""
    
    batch_id: str = Field(..., description="Batch execution ID")
    results: List[BatchItemResult] = Field(..., description="List of execution results")
    summary: Dict[str, Any] = Field(..., description="Batch execution summary")
    dry_run: Optional[bool] = Field(None, description="Whether this was a dry run")
    
    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch-12345",
                "summary": {
                    "total_executions": 2,
                    "successful_executions": 2,
                    "failed_executions": 0,
                    "total_execution_time_ms": 89.5,
                    "avg_execution_time_ms": 44.75,
                    "success_rate": 100.0
                },
                "dry_run": False
            }
        }


class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution."""
    
    process_name: str = Field(..., description="Name of the process/workflow")
    stages: List[str] = Field(default_factory=list, description="List of workflow stage names")
    data: Dict[str, Any] = Field(default_factory=dict, description="Input data dictionary")
    
    @validator('process_name')
    def validate_process_name(cls, v):
        """Validate process_name is not empty."""
        if not v or not v.strip():
            raise ValueError("process_name cannot be empty")
        return v.strip()
    
    @validator('stages')
    def validate_stages(cls, v):
        """Validate all stages are non-empty strings."""
        if not isinstance(v, list):
            raise ValueError("stages must be a list")
        for i, stage in enumerate(v):
            if not isinstance(stage, str) or not stage.strip():
                raise ValueError(f"Stage at index {i} must be a non-empty string")
        return [s.strip() for s in v]
    
    @validator('data')
    def validate_data(cls, v):
        """Validate that data is a dictionary."""
        if not isinstance(v, dict):
            raise ValueError("data must be a dictionary")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "process_name": "ticket_processing",
                "stages": ["NEW", "INPROGESS", "FINISHED"],
                "data": {
                    "ticket_id": "TICK-123",
                    "title": "Issue Report",
                    "priority": "high"
                }
            }
        }


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution."""
    
    process_name: str = Field(..., description="Name of the process/workflow")
    stages: List[str] = Field(..., description="List of executed stages")
    result: Optional[Dict[str, Any]] = Field(None, description="Final workflow result")
    execution_time_ms: Optional[float] = Field(None, description="Total execution time in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "process_name": "ticket_processing",
                "stages": ["NEW", "INPROGESS", "FINISHED"],
                "result": {
                    "status": "completed",
                    "data": {"ticket_id": "TICK-123", "state": "FINISHED"}
                },
                "execution_time_ms": 123.5
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    uptime_seconds: Optional[float] = Field(None, description="Application uptime in seconds")
    environment: Optional[str] = Field(None, description="Environment name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "uptime_seconds": 3600.0,
                "environment": "production"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error_type: str = Field(..., description="Error type/class name")
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for programmatic handling")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_type": "DataValidationError",
                "message": "Input data must be a dictionary",
                "error_code": "DATA_INVALID_TYPE",
                "context": {"data_type": "str"},
                "correlation_id": "req-12345"
            }
        }


# Rule Management Models

class RuleCreateRequest(BaseModel):
    """Request model for creating a rule."""
    
    id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    type: str = Field(default="simple", description="Rule type: 'simple' or 'complex'")
    conditions: Dict[str, Any] = Field(..., description="Conditions dictionary")
    description: str = Field(..., description="Rule description")
    result: str = Field(..., description="Result string")
    weight: Optional[float] = Field(None, description="Weight multiplier")
    rule_point: Optional[float] = Field(None, description="Base points awarded")
    priority: Optional[int] = Field(None, description="Execution priority")
    action_result: Optional[str] = Field(None, description="Action result string")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "R0004",
                "rule_name": "Rule 4",
                "type": "simple",
                "conditions": {"item": "C0004"},
                "description": "Test rule",
                "result": "Y",
                "weight": 0.1,
                "rule_point": 20,
                "priority": 1,
                "action_result": "Y"
            }
        }


class RuleUpdateRequest(BaseModel):
    """Request model for updating a rule."""
    
    rule_name: Optional[str] = Field(None, description="Human-readable rule name")
    type: Optional[str] = Field(None, description="Rule type: 'simple' or 'complex'")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Conditions dictionary")
    description: Optional[str] = Field(None, description="Rule description")
    result: Optional[str] = Field(None, description="Result string")
    weight: Optional[float] = Field(None, description="Weight multiplier")
    rule_point: Optional[float] = Field(None, description="Base points awarded")
    priority: Optional[int] = Field(None, description="Execution priority")
    action_result: Optional[str] = Field(None, description="Action result string")


class RuleResponse(BaseModel):
    """Response model for a rule."""
    
    id: str = Field(..., description="Rule identifier")
    rule_name: str = Field(..., description="Rule name")
    type: Optional[str] = Field(None, description="Rule type")
    conditions: Dict[str, Any] = Field(..., description="Conditions")
    description: str = Field(..., description="Rule description")
    result: str = Field(..., description="Result string")
    weight: Optional[float] = Field(None, description="Weight multiplier")
    rule_point: Optional[float] = Field(None, description="Base points")
    priority: Optional[int] = Field(None, description="Execution priority")
    action_result: Optional[str] = Field(None, description="Action result")


class RulesListResponse(BaseModel):
    """Response model for listing rules."""
    
    rules: List[RuleResponse] = Field(..., description="List of rules")
    count: int = Field(..., description="Total number of rules")


# Condition Management Models

class ConditionCreateRequest(BaseModel):
    """Request model for creating a condition."""
    
    condition_id: str = Field(..., description="Unique condition identifier")
    condition_name: str = Field(..., description="Human-readable condition name")
    attribute: str = Field(..., description="Attribute name to check")
    equation: str = Field(..., description="Equation operator (e.g., 'equal', 'greater_than')")
    constant: Union[str, int, float, List[str]] = Field(..., description="Comparison value")
    
    class Config:
        json_schema_extra = {
            "example": {
                "condition_id": "C0014",
                "condition_name": "Condition 14",
                "attribute": "issue",
                "equation": "greater_than",
                "constant": "30"
            }
        }


class ConditionUpdateRequest(BaseModel):
    """Request model for updating a condition."""
    
    condition_name: Optional[str] = Field(None, description="Human-readable condition name")
    attribute: Optional[str] = Field(None, description="Attribute name to check")
    equation: Optional[str] = Field(None, description="Equation operator")
    constant: Optional[Union[str, int, float, List[str]]] = Field(None, description="Comparison value")


class ConditionResponse(BaseModel):
    """Response model for a condition."""
    
    condition_id: str = Field(..., description="Condition identifier")
    condition_name: str = Field(..., description="Condition name")
    attribute: str = Field(..., description="Attribute name")
    equation: str = Field(..., description="Equation operator")
    constant: Union[str, int, float, List[str]] = Field(..., description="Comparison value")


class ConditionsListResponse(BaseModel):
    """Response model for listing conditions."""
    
    conditions: List[ConditionResponse] = Field(..., description="List of conditions")
    count: int = Field(..., description="Total number of conditions")


# Attribute (Fact) Management Models

class AttributeCreateRequest(BaseModel):
    """Request model for creating an attribute (fact)."""

    attribute_id: str = Field(
        ...,
        description="Unique attribute identifier (key used in conditions and input data)",
    )
    name: str = Field(..., description="Display name for the attribute")
    data_type: str = Field(
        default="string",
        description="Data type: string, number, integer, boolean, date, array, object",
    )
    description: Optional[str] = Field(None, description="Optional description")

    class Config:
        json_schema_extra = {
            "example": {
                "attribute_id": "issue",
                "name": "Issue Number",
                "data_type": "number",
                "description": "Comic issue number",
            }
        }


class AttributeUpdateRequest(BaseModel):
    """Request model for updating an attribute."""

    name: Optional[str] = Field(None, description="Display name")
    data_type: Optional[str] = Field(
        None,
        description="Data type: string, number, integer, boolean, date, array, object",
    )
    description: Optional[str] = Field(None, description="Optional description")
    status: Optional[str] = Field(None, description="Status: active, inactive, etc.")


class AttributeResponse(BaseModel):
    """Response model for an attribute (fact)."""

    attribute_id: str = Field(..., description="Attribute identifier")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Description")
    data_type: str = Field(..., description="Data type")
    status: Optional[str] = Field(None, description="Status")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class AttributesListResponse(BaseModel):
    """Response model for listing attributes."""

    attributes: List[AttributeResponse] = Field(
        ..., description="List of attributes (facts)"
    )
    count: int = Field(..., description="Total number of attributes")


# Action Management Models

class ActionCreateRequest(BaseModel):
    """Request model for creating an action."""
    
    pattern: str = Field(..., description="Pattern string (e.g., 'YYY', 'Y--')")
    message: str = Field(..., description="Action recommendation message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pattern": "YYY",
                "message": "Approved"
            }
        }


class ActionUpdateRequest(BaseModel):
    """Request model for updating an action."""
    
    message: str = Field(..., description="Updated action recommendation message")


class ActionResponse(BaseModel):
    """Response model for an action."""
    
    pattern: str = Field(..., description="Pattern string")
    message: str = Field(..., description="Action recommendation")


class ActionsListResponse(BaseModel):
    """Response model for listing actions."""
    
    actions: Dict[str, str] = Field(..., description="Dictionary mapping patterns to messages")
    count: int = Field(..., description="Total number of actions")


# RuleSet Management Models

class RuleSetCreateRequest(BaseModel):
    """Request model for creating a ruleset."""
    
    ruleset_name: str = Field(..., description="RuleSet name")
    rules: List[Union[str, Dict[str, Any]]] = Field(default_factory=list, description="List of rule IDs or rule dictionaries")
    actionset: List[Union[str, Dict[str, Any]]] = Field(default_factory=list, description="List of pattern strings or action dictionaries")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruleset_name": "my_ruleset",
                "rules": ["R0001", "R0002"],
                "actionset": ["YYY", "Y--"]
            }
        }


class RuleSetUpdateRequest(BaseModel):
    """Request model for updating a ruleset."""
    
    rules: Optional[List[Union[str, Dict[str, Any]]]] = Field(None, description="List of rule IDs or rule dictionaries")
    actionset: Optional[List[Union[str, Dict[str, Any]]]] = Field(None, description="List of pattern strings or action dictionaries")


class RuleSetResponse(BaseModel):
    """Response model for a ruleset."""
    
    ruleset_name: str = Field(..., description="RuleSet name")
    rules: List[Dict[str, Any]] = Field(..., description="List of rules")
    actionset: List[str] = Field(..., description="List of pattern strings")


class RuleSetsListResponse(BaseModel):
    """Response model for listing rulesets."""
    
    rulesets: List[RuleSetResponse] = Field(..., description="List of rulesets")
    count: int = Field(..., description="Total number of rulesets")


# DMN Upload Models

class DMNUploadResponse(BaseModel):
    """Response model for DMN file upload and parsing."""
    
    filename: str = Field(..., description="Name of the uploaded DMN file")
    file_path: str = Field(..., description="Path where the uploaded DMN file was saved")
    rules: List[RuleResponse] = Field(..., description="List of parsed rules in app format")
    patterns: Dict[str, str] = Field(default_factory=dict, description="Dictionary of patterns (if any)")
    rules_count: int = Field(..., description="Total number of parsed rules")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "sample_rules.dmn",
                "file_path": "data/input/sample_rules.dmn",
                "rules": [
                    {
                        "id": "Decision1_R0001",
                        "rule_name": "My Decision - Rule 1",
                        "type": "simple",
                        "conditions": {
                            "attribute": "value",
                            "equation": "greater_than",
                            "constant": "10"
                        },
                        "description": "value greater_than 10",
                        "result": "Approved",
                        "weight": 1.0,
                        "rule_point": 10.0,
                        "priority": 1,
                        "action_result": "Approved"
                    }
                ],
                "patterns": {},
                "rules_count": 1,
                "correlation_id": "req-12345"
            }
        }


class DMNRuleExecutionRequest(BaseModel):
    """Request model for DMN rule execution."""
    
    dmn_file: Optional[str] = Field(None, description="Path to DMN file (relative to data/input or absolute path)")
    dmn_content: Optional[str] = Field(None, description="DMN XML content as string")
    data: Dict[str, Any] = Field(..., description="Input data for rule evaluation")
    dry_run: bool = Field(default=False, description="Execute rules without side effects")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracing")
    
    @validator('data')
    def validate_data(cls, v):
        """Validate that data is a dictionary."""
        if not isinstance(v, dict):
            raise ValueError("data must be a dictionary")
        return v
    
    def validate_dmn_source_provided(self):
        """Validate that exactly one DMN source is provided."""
        sources = [self.dmn_file, self.dmn_content]
        provided = [s for s in sources if s is not None]
        if len(provided) == 0:
            raise ValueError("Exactly one of dmn_file or dmn_content must be provided")
        if len(provided) > 1:
            raise ValueError("Only one of dmn_file or dmn_content can be provided")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dmn_file": "data/input/sample_rules.dmn",
                "data": {
                    "season": "Fall",
                    "guests": 6
                },
                "dry_run": False,
                "correlation_id": "req-12345"
            }
        }

