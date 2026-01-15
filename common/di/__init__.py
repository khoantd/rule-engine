"""
Dependency Injection module.

This module provides dependency injection capabilities for the Rule Engine,
enabling better testability and flexibility in component creation.
"""

from common.di.container import DIContainer, get_container
from common.di.factory import HandlerFactory, RuleEngineFactory

__all__ = [
    'DIContainer',
    'get_container',
    'HandlerFactory',
    'RuleEngineFactory',
]

