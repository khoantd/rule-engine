"""
Configuration management module.

This module provides centralized configuration management with support for:
- Environment-based configuration
- Configuration validation
- Multiple configuration sources (environment variables, files)
- Type-safe configuration access
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import configparser

from common.exceptions import ConfigurationError
from common.logger import get_logger
from common.secrets_manager import get_secrets_manager
from common.security import validate_config_secrets

logger = get_logger(__name__)


@dataclass
class Config:
    """Application configuration."""
    
    # Environment
    environment: str = field(default_factory=lambda: os.getenv('ENVIRONMENT', 'dev'))
    
    # File paths
    rules_config_path: str = field(
        default_factory=lambda: os.getenv(
            'RULES_CONFIG_PATH', 
            'data/input/rules_config_v4.json'
        )
    )
    conditions_config_path: str = field(
        default_factory=lambda: os.getenv(
            'CONDITIONS_CONFIG_PATH', 
            'data/input/conditions_config.json'
        )
    )
    
    # AWS Configuration
    aws_region: str = field(default_factory=lambda: os.getenv('AWS_REGION', 'us-east-1'))
    s3_bucket: Optional[str] = field(default_factory=lambda: os.getenv('S3_BUCKET'))
    s3_config_prefix: str = field(
        default_factory=lambda: os.getenv('S3_CONFIG_PREFIX', 'config/')
    )
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    
    # JIRA Configuration (if needed)
    # Note: Secrets should be loaded from AWS SSM or Secrets Manager in production
    jira_url: Optional[str] = field(default_factory=lambda: os.getenv('JIRA_URL'))
    jira_username: Optional[str] = field(default_factory=lambda: os.getenv('JIRA_USERNAME'))
    jira_token: Optional[str] = field(default_factory=lambda: os.getenv('JIRA_TOKEN'))
    
    # AWS Systems Manager Parameter Store (for secrets)
    use_ssm: bool = field(
        default_factory=lambda: os.getenv('USE_SSM', 'false').lower() == 'true'
    )
    ssm_prefix: str = field(
        default_factory=lambda: os.getenv('SSM_PREFIX', '/rule-engine/')
    )
    
    # Performance
    cache_ttl: int = field(
        default_factory=lambda: int(os.getenv('CACHE_TTL', '3600'))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv('MAX_RETRIES', '3'))
    )
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Create configuration from environment variables.
        
        Returns:
            Config instance
        """
        return cls()
    
    @classmethod
    def from_file(cls, config_file: str = 'config/config.ini') -> 'Config':
        """
        Create configuration from INI file (backward compatibility).
        
        This method loads configuration from an INI file, but for production use,
        secrets should be loaded from AWS SSM Parameter Store or Secrets Manager
        instead of being stored in the config file.
        
        Args:
            config_file: Path to config file
        
        Returns:
            Config instance
        
        Warning:
            This method will attempt to load secrets from AWS SSM/Secrets Manager
            if USE_SSM or USE_SECRETS_MANAGER is enabled, otherwise it will use
            values from the file. In production, never store secrets in config files.
        """
        config = cls()
        
        if not os.path.exists(config_file):
            logger.warning(f"Config file {config_file} not found, using environment defaults")
            return config
        
        parser = configparser.ConfigParser()
        parser.read(config_file)
        
        # Load JIRA config from file if present
        if 'JIRA' in parser:
            config.jira_url = parser.get('JIRA', 'url', fallback=config.jira_url)
            config.jira_username = parser.get('JIRA', 'username', fallback=config.jira_username)
            
            # Try to load token from secrets manager first, fallback to file
            try:
                secrets_manager = get_secrets_manager()
                config.jira_token = secrets_manager.get_secret('jira_token', required=False)
                if config.jira_token:
                    logger.info("JIRA token loaded from secrets manager")
                else:
                    # Fallback to file if not in secrets manager
                    config.jira_token = parser.get('JIRA', 'token', fallback=config.jira_token)
                    if config.jira_token:
                        logger.warning(
                            "JIRA token loaded from config file. "
                            "In production, use secrets manager instead.",
                            secret_key='jira_token'
                        )
            except Exception as e:
                # If secrets manager fails, fallback to file
                logger.warning("Secrets manager not available, using config file", error=str(e))
                config.jira_token = parser.get('JIRA', 'token', fallback=config.jira_token)
        
        # Load RULE config from file if present
        if 'RULE' in parser:
            config.rules_config_path = parser.get(
                'RULE', 
                'file_name', 
                fallback=config.rules_config_path
            )
        
        # Load CONDITIONS config from file if present
        if 'CONDITIONS' in parser:
            config.conditions_config_path = parser.get(
                'CONDITIONS', 
                'file_name', 
                fallback=config.conditions_config_path
            )
        
        # Validate configuration for hard-coded secrets (warns in dev, fails in prod)
        config_dict = {
            'jira_token': config.jira_token,
            'jira_username': config.jira_username,
        }
        if config.is_production():
            # In production, validate strictly
            validate_config_secrets(config_dict)
        
        return config
    
    def validate(self) -> None:
        """
        Validate configuration with security checks.
        
        This method validates:
        - Environment values
        - File paths exist (for local files)
        - Log levels
        - Security concerns (hard-coded secrets in production)
        
        Raises:
            ConfigurationError: If configuration is invalid
            SecurityError: If security validation fails (production only)
        """
        errors = []
        
        # Validate environment
        if self.environment not in ['dev', 'staging', 'prod']:
            errors.append(f"Invalid environment: {self.environment}")
        
        # Validate file paths exist (only for local files, not S3)
        if not self.s3_bucket:
            rules_path = Path(self.rules_config_path)
            if not rules_path.exists():
                errors.append(f"Rules config file not found: {self.rules_config_path}")
            
            conditions_path = Path(self.conditions_config_path)
            if not conditions_path.exists():
                errors.append(f"Conditions config file not found: {self.conditions_config_path}")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}")
        
        # Security validation: Check for hard-coded secrets in production
        if self.is_production():
            config_dict = {
                'jira_token': self.jira_token,
                'jira_username': self.jira_username,
            }
            
            # Validate that secrets are not hard-coded
            # This will log warnings for hard-coded secrets
            validate_config_secrets(config_dict)
        
        # Validate AWS region format (basic check)
        if self.aws_region:
            # Basic region format validation (e.g., us-east-1, eu-west-1)
            region_pattern = r'^[a-z]{2}-[a-z]+-\d+$'
            import re
            if not re.match(region_pattern, self.aws_region):
                errors.append(f"Invalid AWS region format: {self.aws_region}")
        
        # Validate cache TTL is positive
        if self.cache_ttl <= 0:
            errors.append(f"Cache TTL must be positive: {self.cache_ttl}")
        
        # Validate max retries is positive
        if self.max_retries <= 0:
            errors.append(f"Max retries must be positive: {self.max_retries}")
        
        if errors:
            raise ConfigurationError(
                "Configuration validation failed",
                error_code="CONFIG_VALIDATION_ERROR",
                context={'errors': errors}
            )
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == 'prod'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == 'dev'


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance.
    
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        # Try to load from file first, then fall back to environment
        try:
            _config = Config.from_file()
        except Exception as e:
            logger.warning(f"Failed to load config from file: {e}, using environment defaults")
            _config = Config.from_env()
        
        # Validate configuration
        try:
            _config.validate()
        except ConfigurationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    return _config


def set_config(config: Config) -> None:
    """
    Set global configuration instance (useful for testing).
    
    Args:
        config: Config instance to set
    """
    global _config
    _config = config

