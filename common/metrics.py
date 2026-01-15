"""
Metrics collection module for Rule Engine.

This module provides metrics collection capabilities with support for:
- CloudWatch metrics
- Local metrics aggregation
- Performance timing
- Business metrics tracking
"""

import time
import boto3
from contextlib import contextmanager
from typing import Dict, Optional, Any, List
from functools import wraps
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from common.config import get_config
from common.logger import get_logger

logger = get_logger(__name__)


class Metrics:
    """Metrics collection for CloudWatch and local aggregation."""
    
    def __init__(self, namespace: str = 'RuleEngine', use_cloudwatch: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            namespace: CloudWatch namespace for metrics
            use_cloudwatch: Whether to send metrics to CloudWatch
        """
        self.namespace = namespace
        self.use_cloudwatch = use_cloudwatch
        self._local_metrics: Dict[str, list] = {}
        
        # Enhanced analytics tracking
        self._rule_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'executions': 0,
            'matches': 0,
            'total_time_ms': 0.0,
            'min_time_ms': float('inf'),
            'max_time_ms': 0.0
        })
        self._action_metrics: Dict[str, int] = Counter()
        self._pattern_metrics: Dict[str, int] = Counter()
        self._point_metrics: List[float] = []
        
        if use_cloudwatch:
            try:
                self.cloudwatch = boto3.client('cloudwatch')
            except Exception as e:
                logger.warning(f"Failed to initialize CloudWatch client: {e}")
                self.use_cloudwatch = False
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'Count',
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Put a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit (Count, Seconds, Bytes, etc.)
            dimensions: Optional metric dimensions
        """
        # Store locally for aggregation
        if metric_name not in self._local_metrics:
            self._local_metrics[metric_name] = []
        self._local_metrics[metric_name].append({
            'value': value,
            'unit': unit,
            'dimensions': dimensions or {},
            'timestamp': time.time()
        })
        
        # Send to CloudWatch if enabled
        if self.use_cloudwatch:
            try:
                metric_data = {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                }
                
                if dimensions:
                    metric_data['Dimensions'] = [
                        {'Name': k, 'Value': v} 
                        for k, v in dimensions.items()
                    ]
                
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=[metric_data]
                )
            except Exception as e:
                logger.warning(f"Failed to send metric to CloudWatch: {e}")
    
    def increment(
        self,
        metric_name: str,
        value: float = 1.0,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Amount to increment by (default: 1.0)
            dimensions: Optional metric dimensions
        """
        self.put_metric(metric_name, value, 'Count', dimensions)
    
    @contextmanager
    def timer(
        self,
        metric_name: str,
        dimensions: Optional[Dict[str, str]] = None
    ):
        """
        Context manager for timing operations.
        
        Args:
            metric_name: Name of the metric (will be suffixed with '.Duration')
            dimensions: Optional metric dimensions
        
        Example:
            with metrics.timer('rule_execution'):
                # Code to time
                pass
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.put_metric(
                f'{metric_name}.Duration',
                duration,
                'Seconds',
                dimensions
            )
    
    def time_function(
        self,
        metric_name: Optional[str] = None,
        dimensions: Optional[Dict[str, str]] = None
    ):
        """
        Decorator for timing function execution.
        
        Args:
            metric_name: Name of the metric (defaults to function name)
            dimensions: Optional metric dimensions
        
        Example:
            @metrics.time_function('rule_evaluation')
            def evaluate_rule(rule, data):
                # Function implementation
                pass
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                name = metric_name or f"{func.__module__}.{func.__name__}"
                with self.timer(name, dimensions):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_local_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated local metrics.
        
        Returns:
            Dictionary of aggregated metrics
        """
        aggregated = {}
        
        for metric_name, values in self._local_metrics.items():
            if values:
                metric_values = [v['value'] for v in values]
                aggregated[metric_name] = {
                    'count': len(metric_values),
                    'sum': sum(metric_values),
                    'avg': sum(metric_values) / len(metric_values),
                    'min': min(metric_values),
                    'max': max(metric_values),
                }
        
        return aggregated
    
    def clear_local_metrics(self) -> None:
        """Clear local metrics storage."""
        self._local_metrics.clear()
        self._rule_metrics.clear()
        self._action_metrics.clear()
        self._pattern_metrics.clear()
        self._point_metrics.clear()
    
    def track_rule_execution(
        self,
        rule_name: str,
        matched: bool,
        execution_time_ms: float
    ) -> None:
        """
        Track rule execution metrics.
        
        Args:
            rule_name: Name of the rule
            matched: Whether the rule matched
            execution_time_ms: Execution time in milliseconds
        """
        rule_metric = self._rule_metrics[rule_name]
        rule_metric['executions'] += 1
        if matched:
            rule_metric['matches'] += 1
        rule_metric['total_time_ms'] += execution_time_ms
        rule_metric['min_time_ms'] = min(rule_metric['min_time_ms'], execution_time_ms)
        rule_metric['max_time_ms'] = max(rule_metric['max_time_ms'], execution_time_ms)
        
        # Update average
        rule_metric['avg_time_ms'] = (
            rule_metric['total_time_ms'] / rule_metric['executions']
            if rule_metric['executions'] > 0 else 0.0
        )
        
        # Calculate match rate
        rule_metric['match_rate'] = (
            rule_metric['matches'] / rule_metric['executions'] * 100
            if rule_metric['executions'] > 0 else 0.0
        )
    
    def track_action(self, action: str) -> None:
        """
        Track action recommendation.
        
        Args:
            action: Action recommendation string
        """
        if action:
            self._action_metrics[action] += 1
    
    def track_pattern(self, pattern: str) -> None:
        """
        Track pattern result.
        
        Args:
            pattern: Pattern result string
        """
        if pattern:
            self._pattern_metrics[pattern] += 1
    
    def track_points(self, points: float) -> None:
        """
        Track total points.
        
        Args:
            points: Total points value
        """
        self._point_metrics.append(points)
        # Keep only recent points (last 10000)
        if len(self._point_metrics) > 10000:
            self._point_metrics = self._point_metrics[-10000:]
    
    def get_rule_analytics(self, rule_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analytics for rule(s).
        
        Args:
            rule_name: Optional specific rule name, or None for all rules
            
        Returns:
            Dictionary with rule analytics
        """
        if rule_name:
            if rule_name in self._rule_metrics:
                metric = self._rule_metrics[rule_name].copy()
                # Convert inf to None for JSON serialization
                if metric['min_time_ms'] == float('inf'):
                    metric['min_time_ms'] = 0.0
                return {rule_name: metric}
            return {}
        
        # Return all rule metrics
        analytics = {}
        for name, metric in self._rule_metrics.items():
            metric_copy = metric.copy()
            if metric_copy['min_time_ms'] == float('inf'):
                metric_copy['min_time_ms'] = 0.0
            analytics[name] = metric_copy
        
        return analytics
    
    def get_action_analytics(self, top_n: Optional[int] = None) -> Dict[str, Any]:
        """
        Get analytics for action recommendations.
        
        Args:
            top_n: Optional limit on number of results
            
        Returns:
            Dictionary with action analytics
        """
        total = sum(self._action_metrics.values())
        analytics = {
            'total': total,
            'actions': dict(self._action_metrics.most_common(top_n) if top_n else self._action_metrics),
            'distribution': {}
        }
        
        if total > 0:
            for action, count in self._action_metrics.items():
                analytics['distribution'][action] = (count / total * 100)
        
        return analytics
    
    def get_pattern_analytics(self, top_n: Optional[int] = None) -> Dict[str, Any]:
        """
        Get analytics for pattern results.
        
        Args:
            top_n: Optional limit on number of results
            
        Returns:
            Dictionary with pattern analytics
        """
        total = sum(self._pattern_metrics.values())
        analytics = {
            'total': total,
            'patterns': dict(self._pattern_metrics.most_common(top_n) if top_n else self._pattern_metrics),
            'distribution': {}
        }
        
        if total > 0:
            for pattern, count in self._pattern_metrics.items():
                analytics['distribution'][pattern] = (count / total * 100)
        
        return analytics
    
    def get_points_analytics(self) -> Dict[str, Any]:
        """
        Get analytics for total points.
        
        Returns:
            Dictionary with points analytics
        """
        if not self._point_metrics:
            return {
                'count': 0,
                'sum': 0.0,
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0,
                'median': 0.0
            }
        
        sorted_points = sorted(self._point_metrics)
        count = len(sorted_points)
        sum_points = sum(sorted_points)
        
        # Calculate median
        if count % 2 == 0:
            median = (sorted_points[count // 2 - 1] + sorted_points[count // 2]) / 2
        else:
            median = sorted_points[count // 2]
        
        return {
            'count': count,
            'sum': sum_points,
            'avg': sum_points / count if count > 0 else 0.0,
            'min': min(sorted_points),
            'max': max(sorted_points),
            'median': median
        }
    
    def get_comprehensive_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics dashboard data.
        
        Returns:
            Dictionary with all analytics
        """
        return {
            'rules': self.get_rule_analytics(),
            'actions': self.get_action_analytics(),
            'patterns': self.get_pattern_analytics(),
            'points': self.get_points_analytics(),
            'summary': {
                'total_rules_tracked': len(self._rule_metrics),
                'total_executions': sum(
                    m['executions'] for m in self._rule_metrics.values()
                ),
                'total_actions_tracked': sum(self._action_metrics.values()),
                'total_patterns_tracked': sum(self._pattern_metrics.values()),
                'total_points_tracked': len(self._point_metrics)
            }
        }
    
    def get_top_rules(
        self,
        by: str = 'executions',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top rules by specified metric.
        
        Args:
            by: Metric to sort by ('executions', 'matches', 'match_rate', 'avg_time_ms')
            limit: Maximum number of results
            
        Returns:
            List of rule analytics sorted by metric
        """
        if by not in ['executions', 'matches', 'match_rate', 'avg_time_ms']:
            raise ValueError(f"Invalid sort metric: {by}")
        
        rules = []
        for name, metric in self._rule_metrics.items():
            metric_copy = metric.copy()
            metric_copy['rule_name'] = name
            if metric_copy['min_time_ms'] == float('inf'):
                metric_copy['min_time_ms'] = 0.0
            rules.append(metric_copy)
        
        # Sort by specified metric (descending)
        rules.sort(key=lambda x: x[by], reverse=True)
        
        return rules[:limit]


# Global metrics instance
_metrics: Optional[Metrics] = None


def get_metrics() -> Metrics:
    """
    Get global metrics instance.
    
    Returns:
        Metrics instance
    """
    global _metrics
    if _metrics is None:
        config = get_config()
        _metrics = Metrics(
            namespace='RuleEngine',
            use_cloudwatch=config.is_production()
        )
    return _metrics


def set_metrics(metrics: Metrics) -> None:
    """
    Set global metrics instance (useful for testing).
    
    Args:
        metrics: Metrics instance to set
    """
    global _metrics
    _metrics = metrics

