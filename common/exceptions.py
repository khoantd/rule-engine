"""
Custom exception classes for Rule Engine.

This module defines a hierarchy of custom exceptions for better error handling
and error categorization.
"""

from typing import Optional, Dict, Any


class RuleEngineException(Exception):
    """Base exception class for all rule engine exceptions."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize exception.
        
        Args:
            message: Error message
            error_code: Optional error code for programmatic handling
            context: Optional additional context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }


class ConfigurationError(RuleEngineException):
    """Raised when there's an error in configuration."""
    pass


class RuleEvaluationError(RuleEngineException):
    """Raised when rule evaluation fails."""
    pass


class DataValidationError(RuleEngineException):
    """Raised when input data validation fails."""
    pass


class RuleCompilationError(RuleEngineException):
    """Raised when rule compilation fails."""
    pass


class RuleValidationError(RuleEngineException):
    """Raised when rule validation fails (structure, syntax, or dependency)."""
    pass


class ConditionError(RuleEngineException):
    """Raised when condition evaluation fails."""
    pass


class WorkflowError(RuleEngineException):
    """Raised when workflow execution fails."""
    pass


class StorageError(RuleEngineException):
    """Raised when storage operations fail (S3, etc.)."""
    pass


class ExternalServiceError(RuleEngineException):
    """Raised when external service calls fail."""
    pass


class SecurityError(RuleEngineException):
    """Raised when security-related validation fails."""
    pass

