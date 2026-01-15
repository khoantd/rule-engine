"""
Configuration Repository Factory.

This module provides a factory pattern for creating configuration repository instances
based on source type or configuration settings.
"""

from typing import Optional
from enum import Enum

from common.logger import get_logger
from common.exceptions import ConfigurationError
from common.repository.config_repository import (
    ConfigRepository,
    FileConfigRepository,
    S3ConfigRepository
)
from common.config import get_config

logger = get_logger(__name__)


class RepositoryType(Enum):
    """Enumeration of supported repository types."""
    FILE = "file"
    S3 = "s3"


class ConfigRepositoryFactory:
    """
    Factory for creating configuration repository instances.
    
    This factory creates appropriate repository instances based on:
    - Explicit repository type
    - Configuration settings (S3 bucket presence)
    - Source string patterns (S3 keys vs file paths)
    """
    
    @staticmethod
    def create(repository_type: Optional[RepositoryType] = None,
              bucket: Optional[str] = None,
              base_path: Optional[str] = None) -> ConfigRepository:
        """
        Create a configuration repository instance.
        
        Args:
            repository_type: Explicit repository type. If None, auto-detects from config.
            bucket: S3 bucket name (required for S3 repository type)
            base_path: Base path for file repository (optional)
            
        Returns:
            ConfigRepository instance
            
        Raises:
            ConfigurationError: If repository type is invalid or required params missing
            
        Example:
            >>> # Auto-detect from config
            >>> repo = ConfigRepositoryFactory.create()
            >>> # Explicit file repository
            >>> repo = ConfigRepositoryFactory.create(RepositoryType.FILE)
            >>> # Explicit S3 repository
            >>> repo = ConfigRepositoryFactory.create(RepositoryType.S3, bucket='my-bucket')
        """
        # If explicit type provided, use it
        if repository_type == RepositoryType.S3:
            if not bucket:
                # Try to get from config
                config = get_config()
                bucket = config.s3_bucket
            
            if not bucket:
                raise ConfigurationError(
                    "S3 bucket is required for S3 repository type",
                    error_code="S3_BUCKET_REQUIRED",
                    context={'repository_type': repository_type.value}
                )
            
            logger.debug("Creating S3 repository", bucket=bucket)
            return S3ConfigRepository(bucket=bucket)
        
        elif repository_type == RepositoryType.FILE:
            logger.debug("Creating file repository", base_path=base_path)
            return FileConfigRepository(base_path=base_path)
        
        # Auto-detect from configuration
        elif repository_type is None:
            config = get_config()
            
            if config.s3_bucket:
                logger.debug("Auto-detected S3 repository from config", bucket=config.s3_bucket)
                return S3ConfigRepository(bucket=config.s3_bucket)
            else:
                logger.debug("Auto-detected file repository from config")
                return FileConfigRepository(base_path=base_path)
        
        else:
            raise ConfigurationError(
                f"Invalid repository type: {repository_type}",
                error_code="INVALID_REPOSITORY_TYPE",
                context={'repository_type': repository_type}
            )
    
    @staticmethod
    def create_from_source(source: str, bucket: Optional[str] = None) -> ConfigRepository:
        """
        Create repository instance based on source string pattern.
        
        This method attempts to detect the repository type from the source string.
        If source starts with 's3://', creates S3 repository. Otherwise, file repository.
        
        Args:
            source: Source string (file path or S3 key/URI)
            bucket: Optional S3 bucket name (required if source is S3)
            
        Returns:
            ConfigRepository instance
            
        Example:
            >>> # S3 source
            >>> repo = ConfigRepositoryFactory.create_from_source('s3://my-bucket/config.json')
            >>> # File source
            >>> repo = ConfigRepositoryFactory.create_from_source('data/input/config.json')
        """
        if source.startswith('s3://'):
            # Extract bucket and key from S3 URI
            parts = source.replace('s3://', '').split('/', 1)
            if len(parts) == 2:
                bucket = bucket or parts[0]
                logger.debug("Detected S3 source", bucket=bucket, key=parts[1])
                return S3ConfigRepository(bucket=bucket)
            else:
                raise ConfigurationError(
                    f"Invalid S3 URI format: {source}",
                    error_code="INVALID_S3_URI",
                    context={'source': source}
                )
        else:
            # File source
            logger.debug("Detected file source", source=source)
            return FileConfigRepository()

