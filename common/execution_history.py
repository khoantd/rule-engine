"""
Rule Execution History & Audit Trail Module.

This module provides comprehensive execution history tracking including:
- Execution logging with input/output data
- Correlation ID tracking
- Timestamp tracking
- Rule-level execution details
- Query and filter capabilities
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import deque

from common.logger import get_logger
from common.exceptions import ConfigurationError

logger = get_logger(__name__)


@dataclass
class RuleExecutionRecord:
    """Record of a single rule execution."""
    
    execution_id: str
    correlation_id: Optional[str]
    timestamp: float
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    execution_time_ms: float
    rules_evaluated: int
    rules_matched: int
    total_points: float
    pattern_result: str
    action_recommendation: Optional[str]
    rule_evaluations: List[Dict[str, Any]]
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        data = asdict(self)
        data['timestamp_iso'] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


class ExecutionHistory:
    """Manages rule execution history and audit trail."""
    
    def __init__(
        self,
        max_records: int = 10000,
        retention_days: int = 30
    ):
        """
        Initialize execution history.
        
        Args:
            max_records: Maximum number of records to keep in memory
            retention_days: Number of days to retain records
        """
        self.max_records = max_records
        self.retention_days = retention_days
        self._history: deque = deque(maxlen=max_records)
        self._by_correlation_id: Dict[str, List[RuleExecutionRecord]] = {}
        self._by_rule_name: Dict[str, List[RuleExecutionRecord]] = {}
        logger.info("Execution history initialized", 
                   max_records=max_records, retention_days=retention_days)
    
    def log_execution(
        self,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        execution_time_ms: float,
        correlation_id: Optional[str] = None,
        rules_evaluated: int = 0,
        rules_matched: int = 0,
        rule_evaluations: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> str:
        """
        Log a rule execution to history.
        
        Args:
            input_data: Input data dictionary
            output_data: Output data dictionary
            execution_time_ms: Execution time in milliseconds
            correlation_id: Optional correlation ID for request tracing
            rules_evaluated: Number of rules evaluated
            rules_matched: Number of rules that matched
            rule_evaluations: List of per-rule evaluation details
            error: Optional error message
            error_code: Optional error code
            
        Returns:
            Execution ID
        """
        execution_id = str(uuid.uuid4())
        timestamp = time.time()
        
        # Extract output fields
        total_points = output_data.get('total_points', 0.0)
        pattern_result = output_data.get('pattern_result', '')
        action_recommendation = output_data.get('action_recommendation')
        
        record = RuleExecutionRecord(
            execution_id=execution_id,
            correlation_id=correlation_id,
            timestamp=timestamp,
            input_data=input_data,
            output_data=output_data,
            execution_time_ms=execution_time_ms,
            rules_evaluated=rules_evaluated,
            rules_matched=rules_matched,
            total_points=total_points,
            pattern_result=pattern_result,
            action_recommendation=action_recommendation,
            rule_evaluations=rule_evaluations or [],
            error=error,
            error_code=error_code
        )
        
        # Add to history
        self._history.append(record)
        
        # Index by correlation ID
        if correlation_id:
            if correlation_id not in self._by_correlation_id:
                self._by_correlation_id[correlation_id] = []
            self._by_correlation_id[correlation_id].append(record)
        
        # Index by rule names (from rule evaluations)
        if rule_evaluations:
            for eval_data in rule_evaluations:
                rule_name = eval_data.get('rule_name')
                if rule_name:
                    if rule_name not in self._by_rule_name:
                        self._by_rule_name[rule_name] = []
                    self._by_rule_name[rule_name].append(record)
        
        logger.debug("Execution logged", execution_id=execution_id, 
                    correlation_id=correlation_id, execution_time_ms=execution_time_ms)
        
        return execution_id
    
    def get_execution(
        self,
        execution_id: str
    ) -> Optional[RuleExecutionRecord]:
        """
        Get execution record by ID.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution record if found, None otherwise
        """
        for record in self._history:
            if record.execution_id == execution_id:
                return record
        return None
    
    def get_by_correlation_id(
        self,
        correlation_id: str
    ) -> List[RuleExecutionRecord]:
        """
        Get execution records by correlation ID.
        
        Args:
            correlation_id: Correlation ID
            
        Returns:
            List of execution records
        """
        return self._by_correlation_id.get(correlation_id, [])
    
    def get_by_rule_name(
        self,
        rule_name: str,
        limit: Optional[int] = None
    ) -> List[RuleExecutionRecord]:
        """
        Get execution records for a specific rule.
        
        Args:
            rule_name: Rule name to search for
            limit: Optional limit on number of records
            
        Returns:
            List of execution records
        """
        records = self._by_rule_name.get(rule_name, [])
        if limit:
            return records[-limit:]  # Most recent first
        return records
    
    def query(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        min_points: Optional[float] = None,
        max_points: Optional[float] = None,
        pattern_result: Optional[str] = None,
        action_recommendation: Optional[str] = None,
        has_error: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[RuleExecutionRecord]:
        """
        Query execution history with various filters.
        
        Args:
            start_time: Start time filter
            end_time: End time filter
            correlation_id: Correlation ID filter
            rule_name: Rule name filter
            min_points: Minimum total points filter
            max_points: Maximum total points filter
            pattern_result: Pattern result filter
            action_recommendation: Action recommendation filter
            has_error: Filter by error presence
            limit: Maximum number of results
            
        Returns:
            List of matching execution records
        """
        results = []
        start_timestamp = start_time.timestamp() if start_time else None
        end_timestamp = end_time.timestamp() if end_time else None
        
        # Use indexed lookup if possible
        if correlation_id:
            candidates = self.get_by_correlation_id(correlation_id)
        elif rule_name:
            candidates = self.get_by_rule_name(rule_name)
        else:
            candidates = list(self._history)
        
        for record in candidates:
            # Time filter
            if start_timestamp and record.timestamp < start_timestamp:
                continue
            if end_timestamp and record.timestamp > end_timestamp:
                continue
            
            # Points filter
            if min_points is not None and record.total_points < min_points:
                continue
            if max_points is not None and record.total_points > max_points:
                continue
            
            # Pattern result filter
            if pattern_result and record.pattern_result != pattern_result:
                continue
            
            # Action recommendation filter
            if action_recommendation and record.action_recommendation != action_recommendation:
                continue
            
            # Error filter
            if has_error is not None:
                has_error_value = record.error is not None
                if has_error_value != has_error:
                    continue
            
            results.append(record)
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda r: r.timestamp, reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            start_time: Start time for statistics
            end_time: End time for statistics
            
        Returns:
            Dictionary with statistics
        """
        records = self.query(start_time=start_time, end_time=end_time)
        
        if not records:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_rules_evaluated': 0,
                'total_rules_matched': 0,
                'avg_execution_time_ms': 0.0,
                'total_points_sum': 0.0,
                'avg_points': 0.0,
                'pattern_results': {},
                'action_recommendations': {}
            }
        
        successful = sum(1 for r in records if r.error is None)
        failed = len(records) - successful
        
        execution_times = [r.execution_time_ms for r in records]
        points = [r.total_points for r in records]
        
        pattern_results = {}
        action_recommendations = {}
        
        for record in records:
            # Count pattern results
            pattern = record.pattern_result or ''
            pattern_results[pattern] = pattern_results.get(pattern, 0) + 1
            
            # Count action recommendations
            action = record.action_recommendation or 'None'
            action_recommendations[action] = action_recommendations.get(action, 0) + 1
        
        return {
            'total_executions': len(records),
            'successful_executions': successful,
            'failed_executions': failed,
            'total_rules_evaluated': sum(r.rules_evaluated for r in records),
            'total_rules_matched': sum(r.rules_matched for r in records),
            'avg_execution_time_ms': sum(execution_times) / len(execution_times) if execution_times else 0.0,
            'min_execution_time_ms': min(execution_times) if execution_times else 0.0,
            'max_execution_time_ms': max(execution_times) if execution_times else 0.0,
            'total_points_sum': sum(points),
            'avg_points': sum(points) / len(points) if points else 0.0,
            'min_points': min(points) if points else 0.0,
            'max_points': max(points) if points else 0.0,
            'pattern_results': pattern_results,
            'action_recommendations': action_recommendations,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None
        }
    
    def cleanup(self, before_date: Optional[datetime] = None) -> int:
        """
        Cleanup old records.
        
        Args:
            before_date: Remove records before this date (default: retention_days ago)
            
        Returns:
            Number of records removed
        """
        if before_date is None:
            before_date = datetime.now() - timedelta(days=self.retention_days)
        
        before_timestamp = before_date.timestamp()
        
        # Note: deque maxlen automatically removes oldest, but we can still cleanup indexes
        removed = 0
        
        # Cleanup correlation ID index
        for correlation_id in list(self._by_correlation_id.keys()):
            self._by_correlation_id[correlation_id] = [
                r for r in self._by_correlation_id[correlation_id]
                if r.timestamp >= before_timestamp
            ]
            if not self._by_correlation_id[correlation_id]:
                del self._by_correlation_id[correlation_id]
                removed += 1
        
        # Cleanup rule name index
        for rule_name in list(self._by_rule_name.keys()):
            self._by_rule_name[rule_name] = [
                r for r in self._by_rule_name[rule_name]
                if r.timestamp >= before_timestamp
            ]
            if not self._by_rule_name[rule_name]:
                del self._by_rule_name[rule_name]
                removed += 1
        
        logger.info("History cleanup completed", removed_records=removed, before_date=before_date.isoformat())
        return removed
    
    def clear(self) -> None:
        """Clear all execution history."""
        self._history.clear()
        self._by_correlation_id.clear()
        self._by_rule_name.clear()
        logger.info("Execution history cleared")


# Global execution history instance
_history: Optional[ExecutionHistory] = None


def get_execution_history() -> ExecutionHistory:
    """
    Get global execution history instance.
    
    Returns:
        ExecutionHistory instance
    """
    global _history
    if _history is None:
        _history = ExecutionHistory()
    return _history


def set_execution_history(history: ExecutionHistory) -> None:
    """
    Set global execution history instance (useful for testing).
    
    Args:
        history: ExecutionHistory instance
    """
    global _history
    _history = history

