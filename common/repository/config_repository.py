"""
Configuration Repository Pattern Implementation.

This module provides an abstraction layer for configuration loading using the Repository pattern.
It supports multiple configuration sources (file system, S3, etc.) with a unified interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import json
import os

from common.logger import get_logger
from common.exceptions import ConfigurationError, StorageError
from common.json_util import read_json_file, parse_json_v2
from common.s3_aws_util import aws_s3_config_file_read
from common.config import get_config
from common.dmn_parser import DMNParser

logger = get_logger(__name__)


class ConfigRepository(ABC):
    """
    Abstract base class for configuration repositories.

    This class defines the interface for loading configuration data from various sources.
    Implementations should handle source-specific details (file paths, S3 buckets, etc.).
    """

    @abstractmethod
    def read_rules_set(self, source: str) -> List[Dict[str, Any]]:
        """
        Read rules set configuration from the repository source.

        Args:
            source: Source identifier (file path, S3 key, etc.)

        Returns:
            List of rule dictionaries from the "rules_set" key

        Raises:
            ConfigurationError: If configuration cannot be read or parsed
        """
        pass

    @abstractmethod
    def read_conditions_set(self, source: str) -> List[Dict[str, Any]]:
        """
        Read conditions set configuration from the repository source.

        Args:
            source: Source identifier (file path, S3 key, etc.)

        Returns:
            List of condition dictionaries from the "conditions_set" key

        Raises:
            ConfigurationError: If configuration cannot be read or parsed
        """
        pass

    @abstractmethod
    def read_patterns(self, source: str) -> Dict[str, Any]:
        """
        Read patterns/actions configuration from the repository source.

        Args:
            source: Source identifier (file path, S3 key, etc.)

        Returns:
            Dictionary mapping pattern strings to action recommendations

        Raises:
            ConfigurationError: If configuration cannot be read or parsed
        """
        pass

    @abstractmethod
    def read_json(self, source: str) -> Union[Dict[str, Any], List[Any]]:
        """
        Read raw JSON data from the repository source.

        Args:
            source: Source identifier (file path, S3 key, etc.)

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            ConfigurationError: If JSON cannot be read or parsed
        """
        pass


class FileConfigRepository(ConfigRepository):
    """
    File system-based configuration repository.

    This implementation loads configuration from local file system paths.
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize file-based configuration repository.

        Args:
            base_path: Optional base directory for relative paths.
                      If None, paths are resolved relative to current working directory.
        """
        self.base_path = Path(base_path) if base_path else None
        logger.debug("FileConfigRepository initialized", base_path=base_path)

    def _resolve_path(self, source: str) -> str:
        """
        Resolve file path with optional base path.

        Args:
            source: File path (relative or absolute)

        Returns:
            Resolved absolute file path
        """
        if self.base_path:
            # Resolve relative to base path
            return str(self.base_path / source)
        return source

    def read_rules_set(self, source: str) -> List[Dict[str, Any]]:
        """Read rules set from JSON or DMN file."""
        logger.debug("Reading rules set from file", source=source)
        try:
            file_path = self._resolve_path(source)

            # Check if it's a DMN file
            if file_path.lower().endswith(".dmn"):
                return self._read_rules_from_dmn(file_path)

            # Otherwise, treat as JSON
            json_data = read_json_file(file_path)
            parsed_data = parse_json_v2("$.rules_set", json_data)

            if not parsed_data or (isinstance(parsed_data, int) and parsed_data == 0):
                logger.warning("No rules found in configuration", source=source)
                return []

            if isinstance(parsed_data, list):
                logger.info(
                    "Rules set loaded successfully",
                    source=source,
                    rules_count=len(parsed_data),
                )
                return parsed_data
            else:
                logger.warning(
                    "Unexpected rules set format",
                    source=source,
                    data_type=type(parsed_data).__name__,
                )
                return []
        except Exception as e:
            logger.error(
                "Failed to read rules set from file",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read rules set from {source}: {str(e)}",
                error_code="RULES_SET_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e

    def _read_rules_from_dmn(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Read rules from DMN file.

        Args:
            file_path: Path to DMN XML file

        Returns:
            List of rule dictionaries

        Raises:
            ConfigurationError: If DMN file cannot be parsed
        """
        logger.debug("Reading rules from DMN file", file_path=file_path)
        try:
            parser = DMNParser()
            result = parser.parse_file(file_path)
            rules = result.get("rules_set", [])

            logger.info(
                "Rules loaded from DMN file",
                file_path=file_path,
                rules_count=len(rules),
            )

            return rules
        except Exception as e:
            logger.error(
                "Failed to read rules from DMN file",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read rules from DMN file {file_path}: {str(e)}",
                error_code="DMN_RULES_READ_ERROR",
                context={"file_path": file_path, "error": str(e)},
            ) from e

    def read_conditions_set(self, source: str) -> List[Dict[str, Any]]:
        """Read conditions set from JSON file."""
        logger.debug("Reading conditions set from file", source=source)
        try:
            file_path = self._resolve_path(source)
            json_data = read_json_file(file_path)
            parsed_data = parse_json_v2("$.conditions_set", json_data)

            if not parsed_data or (isinstance(parsed_data, int) and parsed_data == 0):
                logger.warning("No conditions found in configuration", source=source)
                return []

            if isinstance(parsed_data, list):
                logger.info(
                    "Conditions set loaded successfully",
                    source=source,
                    conditions_count=len(parsed_data),
                )
                return parsed_data
            else:
                logger.warning(
                    "Unexpected conditions set format",
                    source=source,
                    data_type=type(parsed_data).__name__,
                )
                return []
        except Exception as e:
            logger.error(
                "Failed to read conditions set from file",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read conditions set from {source}: {str(e)}",
                error_code="CONDITIONS_SET_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e

    def read_patterns(self, source: str) -> Dict[str, Any]:
        """Read patterns/actions from JSON file."""
        logger.debug("Reading patterns from file", source=source)
        try:
            file_path = self._resolve_path(source)
            json_data = read_json_file(file_path)
            parsed_data = parse_json_v2("$.patterns", json_data)

            if not parsed_data or (isinstance(parsed_data, int) and parsed_data == 0):
                logger.warning("No patterns found in configuration", source=source)
                return {}

            if isinstance(parsed_data, dict):
                logger.info(
                    "Patterns loaded successfully",
                    source=source,
                    patterns_count=len(parsed_data),
                )
                return parsed_data
            else:
                logger.warning(
                    "Unexpected patterns format",
                    source=source,
                    data_type=type(parsed_data).__name__,
                )
                return {}
        except Exception as e:
            logger.error(
                "Failed to read patterns from file",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read patterns from {source}: {str(e)}",
                error_code="PATTERNS_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e

    def read_json(self, source: str) -> Union[Dict[str, Any], List[Any]]:
        """
        Read raw JSON from file, or convert DMN to JSON format.

        Args:
            source: File path (JSON or DMN)

        Returns:
            Parsed JSON data (dict or list)
        """
        logger.debug("Reading JSON/DMN from file", source=source)
        try:
            file_path = self._resolve_path(source)

            # Check if it's a DMN file
            if file_path.lower().endswith(".dmn"):
                parser = DMNParser()
                result = parser.parse_file(file_path)
                logger.info("DMN converted to JSON format", source=source)
                return result

            # Otherwise, treat as JSON
            json_data = read_json_file(file_path)
            logger.info("JSON loaded successfully", source=source)
            return json_data
        except Exception as e:
            logger.error(
                "Failed to read JSON/DMN from file",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read JSON/DMN from {source}: {str(e)}",
                error_code="JSON_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e


class S3ConfigRepository(ConfigRepository):
    """
    S3-based configuration repository.

    This implementation loads configuration from AWS S3 buckets.
    """

    def __init__(self, bucket: Optional[str] = None):
        """
        Initialize S3-based configuration repository.

        Args:
            bucket: S3 bucket name. If None, uses bucket from config or environment.
        """
        # Get bucket from configuration if not provided
        if bucket:
            self.bucket = bucket
        else:
            try:
                from common.config import get_config

                config = get_config()
                self.bucket = config.s3_bucket or os.getenv(
                    "S3_BUCKET_RULE_CONFIG", "rule-config-file"
                )
            except Exception:
                # Fallback to environment variable or default
                self.bucket = os.getenv(
                    "S3_BUCKET_RULE_CONFIG", os.getenv("S3_BUCKET", "rule-config-file")
                )
        logger.debug("S3ConfigRepository initialized", bucket=self.bucket)

    def _read_from_s3(self, key: str) -> str:
        """
        Read file content from S3.

        Args:
            key: S3 object key

        Returns:
            File content as string

        Raises:
            StorageError: If S3 read fails
        """
        try:
            return aws_s3_config_file_read(self.bucket, key)
        except Exception as e:
            logger.error(
                "Failed to read from S3",
                bucket=self.bucket,
                key=key,
                error=str(e),
                exc_info=True,
            )
            raise StorageError(
                f"Failed to read {key} from S3 bucket {self.bucket}: {str(e)}",
                error_code="S3_READ_ERROR",
                context={"bucket": self.bucket, "key": key, "error": str(e)},
            ) from e

    def read_rules_set(self, source: str) -> List[Dict[str, Any]]:
        """Read rules set from S3."""
        logger.debug("Reading rules set from S3", source=source, bucket=self.bucket)
        try:
            content = self._read_from_s3(source)
            json_data = json.loads(content)
            parsed_data = parse_json_v2("$.rules_set", json_data)

            if not parsed_data or (isinstance(parsed_data, int) and parsed_data == 0):
                logger.warning("No rules found in S3 configuration", source=source)
                return []

            if isinstance(parsed_data, list):
                logger.info(
                    "Rules set loaded from S3",
                    source=source,
                    rules_count=len(parsed_data),
                )
                return parsed_data
            else:
                logger.warning(
                    "Unexpected rules set format",
                    source=source,
                    data_type=type(parsed_data).__name__,
                )
                return []
        except Exception as e:
            logger.error(
                "Failed to read rules set from S3",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read rules set from S3 {source}: {str(e)}",
                error_code="RULES_SET_S3_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e

    def read_conditions_set(self, source: str) -> List[Dict[str, Any]]:
        """Read conditions set from S3."""
        logger.debug(
            "Reading conditions set from S3", source=source, bucket=self.bucket
        )
        try:
            content = self._read_from_s3(source)
            json_data = json.loads(content)
            parsed_data = parse_json_v2("$.conditions_set", json_data)

            if not parsed_data or (isinstance(parsed_data, int) and parsed_data == 0):
                logger.warning("No conditions found in S3 configuration", source=source)
                return []

            if isinstance(parsed_data, list):
                logger.info(
                    "Conditions set loaded from S3",
                    source=source,
                    conditions_count=len(parsed_data),
                )
                return parsed_data
            else:
                logger.warning(
                    "Unexpected conditions set format",
                    source=source,
                    data_type=type(parsed_data).__name__,
                )
                return []
        except Exception as e:
            logger.error(
                "Failed to read conditions set from S3",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read conditions set from S3 {source}: {str(e)}",
                error_code="CONDITIONS_SET_S3_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e

    def read_patterns(self, source: str) -> Dict[str, Any]:
        """Read patterns/actions from S3."""
        logger.debug("Reading patterns from S3", source=source, bucket=self.bucket)
        try:
            content = self._read_from_s3(source)
            json_data = json.loads(content)
            parsed_data = parse_json_v2("$.patterns", json_data)

            if not parsed_data or (isinstance(parsed_data, int) and parsed_data == 0):
                logger.warning("No patterns found in S3 configuration", source=source)
                return {}

            if isinstance(parsed_data, dict):
                logger.info(
                    "Patterns loaded from S3",
                    source=source,
                    patterns_count=len(parsed_data),
                )
                return parsed_data
            else:
                logger.warning(
                    "Unexpected patterns format",
                    source=source,
                    data_type=type(parsed_data).__name__,
                )
                return {}
        except Exception as e:
            logger.error(
                "Failed to read patterns from S3",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read patterns from S3 {source}: {str(e)}",
                error_code="PATTERNS_S3_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e

    def read_json(self, source: str) -> Union[Dict[str, Any], List[Any]]:
        """Read raw JSON from S3."""
        logger.debug("Reading JSON from S3", source=source, bucket=self.bucket)
        try:
            content = self._read_from_s3(source)
            json_data = json.loads(content)
            logger.info("JSON loaded from S3", source=source)
            return json_data
        except Exception as e:
            logger.error(
                "Failed to read JSON from S3",
                source=source,
                error=str(e),
                exc_info=True,
            )
            raise ConfigurationError(
                f"Failed to read JSON from S3 {source}: {str(e)}",
                error_code="JSON_S3_READ_ERROR",
                context={"source": source, "error": str(e)},
            ) from e


# Global repository instance
_repository: Optional[ConfigRepository] = None


def get_config_repository() -> ConfigRepository:
    """
    Get the global configuration repository instance.

    This function returns a repository instance based on the current configuration.
    Priority order:
    1. Database repository (if USE_DATABASE=true and DATABASE_URL is set)
    2. S3 repository (if S3 bucket is configured)
    3. File repository (default)

    Returns:
        ConfigRepository instance (DatabaseConfigRepository, S3ConfigRepository, or FileConfigRepository)
    """
    global _repository

    if _repository is None:
        config = get_config()

        # Check if database should be used
        if config.use_database and config.database_url:
            logger.info("Using database configuration repository")
            from common.repository.db_repository import DatabaseConfigRepository

            _repository = DatabaseConfigRepository()
        # Check if S3 should be used
        elif config.s3_bucket:
            logger.info("Using S3 configuration repository", bucket=config.s3_bucket)
            _repository = S3ConfigRepository(bucket=config.s3_bucket)
        # Default to file repository
        else:
            logger.info("Using file system configuration repository")
            _repository = FileConfigRepository()

    return _repository


def set_config_repository(repository: ConfigRepository) -> None:
    """
    Set the global configuration repository instance (useful for testing).

    Args:
        repository: ConfigRepository instance to set
    """
    global _repository
    _repository = repository
    logger.debug(
        "Configuration repository set", repository_type=type(repository).__name__
    )
