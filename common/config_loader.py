"""
Configuration Loader Module.

This module provides a clean separation between configuration loading and execution logic.
It uses the repository pattern for configuration access.
"""

from typing import Any, Dict, List, Optional
from functools import lru_cache
from pathlib import Path

from common.logger import get_logger
from common.exceptions import ConfigurationError
from common.repository import get_config_repository, ConfigRepository
from common.util import cfg_read
from common.cache import memoize_with_cache

logger = get_logger(__name__)


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
        logger.debug("ConfigLoader initialized", 
                    repository_type=type(self.repository).__name__)
    
    @memoize_with_cache(
        key_func=lambda self: "rules_set_config",
        file_paths=lambda self: [cfg_read("RULE", "file_name")] if Path('config/config.ini').exists() else []
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
            config_file = cfg_read("RULE", "file_name")
            logger.debug("Rules config file path", config_file=config_file)
            rules = self.repository.read_rules_set(config_file)
            
            if not rules:
                logger.warning("No rules found in configuration", config_file=config_file)
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
                context={'error': str(e)}
            ) from e
    
    @memoize_with_cache(
        key_func=lambda self: "actions_set_config",
        file_paths=lambda self: [cfg_read("RULE", "file_name")] if Path('config/config.ini').exists() else []
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
            config_file = cfg_read("RULE", "file_name")
            logger.debug("Actions config file path", config_file=config_file)
            actions = self.repository.read_patterns(config_file)
            
            if not actions:
                logger.warning("No actions found in configuration", config_file=config_file)
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
                context={'error': str(e)}
            ) from e
    
    @memoize_with_cache(
        key_func=lambda self: "conditions_set_config",
        file_paths=lambda self: [cfg_read("CONDITIONS", "file_name")] if Path('config/config.ini').exists() else []
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
                context={'error': str(e)}
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
    logger.debug("Set global config loader", 
                loader_type=type(loader).__name__)

