"""
Configuration repository module.

This module provides an abstraction layer for configuration loading from multiple sources
(file system, S3, etc.) using the Repository pattern.
"""

from common.repository.config_repository import (
    ConfigRepository,
    FileConfigRepository,
    S3ConfigRepository,
    get_config_repository
)
from common.repository.config_factory import ConfigRepositoryFactory

__all__ = [
    'ConfigRepository',
    'FileConfigRepository',
    'S3ConfigRepository',
    'get_config_repository',
    'ConfigRepositoryFactory',
]

