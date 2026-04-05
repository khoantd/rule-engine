"""
Configuration management module.

This module provides centralized configuration management with support for:
- Environment-based configuration
- Configuration validation
- Multiple configuration sources (environment variables, files)
- Type-safe configuration access
"""

import os

# Load .env early so USE_DATABASE, TIMESCALE_SERVICE_URL, DATABASE_URL are available
try:
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv())
except ImportError:
    pass
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
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "dev"))

    # File paths
    rules_config_path: str = field(
        default_factory=lambda: os.getenv("RULES_CONFIG_PATH", "data/input/rules_config_v4.json")
    )
    conditions_config_path: str = field(
        default_factory=lambda: os.getenv(
            "CONDITIONS_CONFIG_PATH", "data/input/conditions_config.json"
        )
    )

    # When using DatabaseConfigRepository, rules / patterns load from this ruleset name.
    # Env wins over config.ini; see [RULE] default_ruleset_name in config file.
    default_ruleset_name: Optional[str] = field(
        default_factory=lambda: (os.getenv("DEFAULT_RULESET_NAME") or "").strip() or None
    )

    # When True (default), rules_exec loads from config/ruleset only rules whose condition
    # attributes are all present as top-level keys in input data. Set RULE_ENGINE_FILTER_RULES_BY_INPUT_KEYS=false to disable.
    filter_rules_by_input_keys: bool = field(
        default_factory=lambda: os.getenv("RULE_ENGINE_FILTER_RULES_BY_INPUT_KEYS", "true").lower()
        not in ("0", "false", "no")
    )

    # When True, POST /api/v1/rules/{ruleset}/execute requires a registered active consumer
    # and an active registration for that ruleset (requires USE_DATABASE).
    require_consumer_ruleset_registration: bool = field(
        default_factory=lambda: os.getenv("REQUIRE_CONSUMER_RULESET_REGISTRATION", "false").lower()
        == "true"
    )

    # AWS Configuration
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    s3_bucket: Optional[str] = field(default_factory=lambda: os.getenv("S3_BUCKET"))
    s3_config_prefix: str = field(default_factory=lambda: os.getenv("S3_CONFIG_PREFIX", "config/"))

    # Database Configuration
    use_database: bool = field(
        default_factory=lambda: os.getenv("USE_DATABASE", "false").lower() == "true"
    )
    database_url: Optional[str] = field(
        default_factory=lambda: os.getenv("TIMESCALE_SERVICE_URL") or os.getenv("DATABASE_URL")
    )
    database_env_file: Optional[str] = field(default_factory=lambda: os.getenv("DATABASE_ENV_FILE"))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # JIRA Configuration (if needed)
    # Note: Secrets should be loaded from AWS SSM or Secrets Manager in production
    jira_url: Optional[str] = field(default_factory=lambda: os.getenv("JIRA_URL"))
    jira_username: Optional[str] = field(default_factory=lambda: os.getenv("JIRA_USERNAME"))
    jira_token: Optional[str] = field(default_factory=lambda: os.getenv("JIRA_TOKEN"))

    # AWS Systems Manager Parameter Store (for secrets)
    use_ssm: bool = field(default_factory=lambda: os.getenv("USE_SSM", "false").lower() == "true")
    ssm_prefix: str = field(default_factory=lambda: os.getenv("SSM_PREFIX", "/rule-engine/"))

    # Performance
    cache_ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL", "3600")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "3")))

    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.

        Returns:
            Config instance
        """
        return cls()

    @classmethod
    def from_file(cls, config_file: str = "config/config.ini") -> "Config":
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
        if "JIRA" in parser:
            config.jira_url = parser.get("JIRA", "url", fallback=config.jira_url)
            config.jira_username = parser.get("JIRA", "username", fallback=config.jira_username)

            # Token priority: SSM / Secrets Manager / JIRA_TOKEN env (via get_secret), then INI file.
            secrets_manager = get_secrets_manager()
            token_from_vault: Optional[str] = None
            try:
                token_from_vault = secrets_manager.get_secret("jira_token", required=False)
            except Exception as e:
                logger.warning(
                    "Secrets manager error while resolving JIRA token",
                    error=str(e),
                    secret_key="jira_token",
                )

            raw_file_token = (parser.get("JIRA", "token", fallback="") or "").strip()

            if token_from_vault:
                config.jira_token = token_from_vault
                # DEBUG: this path often runs twice if code calls Config.from_file after
                # package import (get_config() is triggered early via common.cache.FileCache).
                logger.debug(
                    "JIRA token resolved (SSM, Secrets Manager, or JIRA_TOKEN env)",
                    secret_key="jira_token",
                )
            elif raw_file_token:
                config.jira_token = raw_file_token
                logger.warning(
                    "JIRA token loaded from config file. "
                    "Set JIRA_TOKEN or use AWS SSM / Secrets Manager instead.",
                    secret_key="jira_token",
                )
            # else: keep token from cls() default (typically unset if JIRA_TOKEN missing)

        # Load RULE config from file if present
        if "RULE" in parser:
            config.rules_config_path = parser.get(
                "RULE", "file_name", fallback=config.rules_config_path
            )
            # DB repository: optional explicit ruleset (ignored when DEFAULT_RULESET_NAME is set)
            if not os.getenv("DEFAULT_RULESET_NAME"):
                ini_rs = parser.get("RULE", "default_ruleset_name", fallback="").strip()
                if not ini_rs:
                    ini_rs = parser.get("RULE", "ruleset_name", fallback="").strip()
                if ini_rs:
                    config.default_ruleset_name = ini_rs
            if not os.getenv("RULE_ENGINE_FILTER_RULES_BY_INPUT_KEYS"):
                if "filter_rules_by_input_keys" in parser["RULE"]:
                    val = parser.get("RULE", "filter_rules_by_input_keys", fallback="true")
                    config.filter_rules_by_input_keys = str(val).strip().lower() not in (
                        "0",
                        "false",
                        "no",
                    )

        # Load CONDITIONS config from file if present
        if "CONDITIONS" in parser:
            config.conditions_config_path = parser.get(
                "CONDITIONS", "file_name", fallback=config.conditions_config_path
            )

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

        # Validate environment (Docker / platforms often use "production")
        env_lower = (self.environment or "").strip().lower()
        if env_lower not in ("dev", "staging", "prod", "production"):
            errors.append(f"Invalid environment: {self.environment}")

        # Validate file paths exist (only when rules/conditions are loaded from local files)
        if not self.s3_bucket and not self.use_database:
            rules_path = Path(self.rules_config_path)
            if not rules_path.exists():
                errors.append(f"Rules config file not found: {self.rules_config_path}")

            conditions_path = Path(self.conditions_config_path)
            if not conditions_path.exists():
                errors.append(f"Conditions config file not found: {self.conditions_config_path}")

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}")

        # Security validation: Check for hard-coded secrets in production
        if self.is_production():
            config_dict = {
                "jira_token": self.jira_token,
                "jira_username": self.jira_username,
            }

            # Validate that secrets are not hard-coded
            # This will log warnings for hard-coded secrets
            validate_config_secrets(config_dict)

        # Validate AWS region format (basic check)
        if self.aws_region:
            # Basic region format validation (e.g., us-east-1, eu-west-1)
            region_pattern = r"^[a-z]{2}-[a-z]+-\d+$"
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
                context={"errors": errors},
            )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return (self.environment or "").strip().lower() in ("prod", "production")

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "dev"


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
            err_list = e.context.get("errors") if e.context else None
            logger.error(
                "Configuration validation failed",
                message=str(e),
                error_code=e.error_code,
                validation_errors=err_list,
                context=e.context,
            )
            _config = None
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
