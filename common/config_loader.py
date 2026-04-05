"""
Configuration Loader Module.

This module provides a clean separation between configuration loading and execution logic.
It uses the repository pattern for configuration access.
"""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from common.logger import get_logger
from common.exceptions import ConfigurationError
from common.repository import get_config_repository, ConfigRepository
from common.util import cfg_read
from common.cache import memoize_with_cache

logger = get_logger(__name__)


def _looks_like_file_based_rules_ref(file_name_value: str) -> bool:
    """
    True if ``RULE.file_name`` is a filesystem-style reference, not a DB ruleset name.

    Used so database mode does not query for a ruleset named like ``data/input/x.json``.
    """
    s = (file_name_value or "").strip()
    if not s:
        return False
    lower = s.lower()
    if "/" in s or "\\" in s:
        return True
    if lower.endswith(".json") or lower.endswith(".dmn"):
        return True
    return False


def _resolve_rules_source_for_repository(
    repository: ConfigRepository,
    file_name_cfg: str,
) -> Optional[str]:
    """
    Resolve the ``source`` argument for ``read_rules_set`` / ``read_patterns``.

    File and S3 repositories receive ``file_name_cfg`` unchanged. The database
    repository uses ``Config.default_ruleset_name`` when set; otherwise, if
    ``file_name_cfg`` looks like a file path, returns ``None`` so the DB layer
    uses its default-ruleset resolution chain instead of a bogus name lookup.
    """
    from common.repository.db_repository import DatabaseConfigRepository
    from common.config import get_config

    if isinstance(repository, DatabaseConfigRepository):
        explicit = get_config().default_ruleset_name
        if explicit and str(explicit).strip():
            name = str(explicit).strip()
            logger.debug(
                "Using configured default ruleset name for database repository",
                ruleset_name=name,
            )
            return name
        if _looks_like_file_based_rules_ref(file_name_cfg):
            logger.info(
                "Database repository: RULE.file_name looks like a file path; "
                "skipping ruleset name lookup. Using default ruleset resolution "
                "(set DEFAULT_RULESET_NAME or [RULE] default_ruleset_name to pick a ruleset).",
                file_name=file_name_cfg,
            )
            return None
        return (file_name_cfg or "").strip() or None
    return file_name_cfg


def _rules_cache_key_fragment(loader: "ConfigLoader") -> str:
    """Stable cache key part for rules/actions loads (repository + resolved source)."""
    from common.repository.db_repository import DatabaseConfigRepository
    from common.config import get_config

    file_name = cfg_read("RULE", "file_name")
    if isinstance(loader.repository, DatabaseConfigRepository):
        resolved = _resolve_rules_source_for_repository(loader.repository, file_name)
        drn = get_config().default_ruleset_name or ""
        return f"db|ref={file_name!r}|resolved={resolved!r}|explicit={drn!r}"
    return f"file|ref={file_name!r}"


def _rules_set_cache_watch_paths(loader: "ConfigLoader") -> List[str]:
    """Config and rule files whose changes should invalidate cached rules/actions."""
    paths: List[str] = []
    cfg_p = Path(os.getenv("CONFIG_FILE_PATH", "config/config.ini"))
    if cfg_p.exists():
        paths.append(str(cfg_p.resolve()))
    try:
        rule_ref = cfg_read("RULE", "file_name")
        from common.repository.db_repository import DatabaseConfigRepository

        if isinstance(loader.repository, DatabaseConfigRepository):
            return paths
        rpath = Path(rule_ref)
        if rpath.exists():
            paths.append(str(rpath.resolve()))
    except Exception:
        pass
    return paths


class ConfigLoader:
    """
    Configuration loader that uses repository pattern for configuration access.

    This class separates configuration loading from execution logic,
    making the code more maintainable and testable.
    """

    def __init__(self, repository: Optional[ConfigRepository] = None):
        """
        Initialize configuration loader.

        Args:
            repository: Optional configuration repository. If None, uses global repository.
        """
        self.repository = repository or get_config_repository()
        logger.debug("ConfigLoader initialized", repository_type=type(self.repository).__name__)

    @memoize_with_cache(
        key_func=lambda self: f"rules_set_config:{_rules_cache_key_fragment(self)}",
        file_paths=lambda self: _rules_set_cache_watch_paths(self),
    )
    def load_rules_set(self) -> List[Dict[str, Any]]:
        """
        Load rules set configuration (cached).

        Returns:
            List of rule dictionaries from configuration

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        logger.debug("Loading rules set configuration")
        try:
            rule_ref = cfg_read("RULE", "file_name")
            source = _resolve_rules_source_for_repository(self.repository, rule_ref)
            logger.debug(
                "Rules load source resolved",
                rule_ref=rule_ref,
                repository_source=source,
            )
            rules = self.repository.read_rules_set(source)

            if not rules:
                logger.warning("No rules found in configuration", rule_ref=rule_ref, source=source)
                return []

            logger.info("Rules set loaded successfully", rules_count=len(rules))
            return rules

        except ConfigurationError:
            raise
        except Exception as e:
            logger.error("Failed to load rules set", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to load rules set: {str(e)}",
                error_code="RULES_SET_LOAD_ERROR",
                context={"error": str(e)},
            ) from e

    @memoize_with_cache(
        key_func=lambda self: f"actions_set_config:{_rules_cache_key_fragment(self)}",
        file_paths=lambda self: _rules_set_cache_watch_paths(self),
    )
    def load_actions_set(self) -> Dict[str, Any]:
        """
        Load actions/patterns configuration (cached).

        Returns:
            Dictionary mapping pattern strings to action recommendations

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        logger.debug("Loading actions set configuration")
        try:
            rule_ref = cfg_read("RULE", "file_name")
            source = _resolve_rules_source_for_repository(self.repository, rule_ref)
            logger.debug(
                "Actions/patterns load source resolved",
                rule_ref=rule_ref,
                repository_source=source,
            )
            actions = self.repository.read_patterns(source)

            if not actions:
                logger.warning(
                    "No actions found in configuration", rule_ref=rule_ref, source=source
                )
                return {}

            logger.info("Actions set loaded successfully", actions_count=len(actions))
            return actions

        except ConfigurationError:
            raise
        except Exception as e:
            logger.error("Failed to load actions set", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to load actions set: {str(e)}",
                error_code="ACTIONS_SET_LOAD_ERROR",
                context={"error": str(e)},
            ) from e

    @memoize_with_cache(
        key_func=lambda self: "conditions_set_config",
        file_paths=lambda self: [cfg_read("CONDITIONS", "file_name")]
        if Path("config/config.ini").exists()
        else [],
    )
    def load_conditions_set(self) -> List[Dict[str, Any]]:
        """
        Load conditions set configuration (cached).

        Returns:
            List of condition dictionaries from configuration

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        logger.debug("Loading conditions set configuration")
        try:
            config_file = cfg_read("CONDITIONS", "file_name")
            logger.debug("Conditions config file path", config_file=config_file)
            conditions = self.repository.read_conditions_set(config_file)

            if not conditions:
                logger.warning("No conditions found in configuration", config_file=config_file)
                return []

            logger.info("Conditions set loaded successfully", conditions_count=len(conditions))
            return conditions

        except ConfigurationError:
            raise
        except Exception as e:
            logger.error("Failed to load conditions set", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to load conditions set: {str(e)}",
                error_code="CONDITIONS_SET_LOAD_ERROR",
                context={"error": str(e)},
            ) from e


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """
    Get the global configuration loader instance.

    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
        logger.debug("Created global config loader")
    return _config_loader


def set_config_loader(loader: ConfigLoader) -> None:
    """
    Set the global configuration loader instance (useful for testing).

    Args:
        loader: ConfigLoader instance to set
    """
    global _config_loader
    _config_loader = loader
    logger.debug("Set global config loader", loader_type=type(loader).__name__)
