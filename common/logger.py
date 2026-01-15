"""
Structured logging module for Rule Engine.

This module provides structured logging capabilities with support for:
- JSON formatted logs
- Correlation IDs for request tracing
- Multiple log levels
- Contextual logging
"""

import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        # Add any extra context
        if hasattr(record, 'extra_context'):
            log_data.update(record.extra_context)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with correlation ID support."""
    
    def __init__(
        self, 
        name: str, 
        level: int = logging.INFO,
        use_json: bool = True,
        stream: Any = sys.stdout
    ):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically __name__)
            level: Logging level (default: INFO)
            use_json: Whether to use JSON formatting (default: True)
            stream: Output stream (default: sys.stdout)
        """
        self.logger = logging.getLogger(name)
        
        # Remove existing handlers to avoid duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        handler = logging.StreamHandler(stream)
        
        if use_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
            )
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(level)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _log(
        self, 
        level: int, 
        message: str, 
        correlation_id: Optional[str] = None,
        exc_info: Optional[bool] = None,
        **kwargs
    ):
        """Internal log method with correlation ID support."""
        extra = {}
        if correlation_id:
            extra['correlation_id'] = correlation_id
        
        if kwargs:
            extra['extra_context'] = kwargs
        
        # Handle exception info properly
        if exc_info:
            self.logger.log(level, message, extra=extra if extra else None, exc_info=True)
        else:
            self.logger.log(level, message, extra=extra if extra else None)
    
    def debug(
        self, 
        message: str, 
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """Log debug message."""
        self._log(logging.DEBUG, message, correlation_id, **kwargs)
    
    def info(
        self, 
        message: str, 
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """Log info message."""
        self._log(logging.INFO, message, correlation_id, **kwargs)
    
    def warning(
        self, 
        message: str, 
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        """Log warning message."""
        self._log(logging.WARNING, message, correlation_id, **kwargs)
    
    def error(
        self, 
        message: str, 
        correlation_id: Optional[str] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """Log error message."""
        self._log(logging.ERROR, message, correlation_id, exc_info=exc_info, **kwargs)
    
    def critical(
        self, 
        message: str, 
        correlation_id: Optional[str] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """Log critical message."""
        self._log(logging.CRITICAL, message, correlation_id, exc_info=exc_info, **kwargs)


# Convenience function to get logger instance
def get_logger(name: str, level: Optional[int] = None) -> StructuredLogger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        level: Optional logging level override
    
    Returns:
        StructuredLogger instance
    """
    log_level = level or logging.INFO
    return StructuredLogger(name, level=log_level)

