import os
import configparser
from pathlib import Path
from typing import Optional
from functools import lru_cache
from common.exceptions import ConfigurationError
from common.logger import get_logger
from common.cache import memoize_with_cache, get_file_cache

logger = get_logger(__name__)


def _get_config_file_path() -> str:
    """
    Get configuration file path from configuration.
    
    Returns:
        Path to configuration file
    """
    try:
        from common.config import get_config
        config = get_config()
        # Config file path can be set via environment variable
        return os.getenv('CONFIG_FILE_PATH', 'config/config.ini')
    except Exception:
        # Fallback to default
        return 'config/config.ini'

@memoize_with_cache(
    key_func=lambda section, parameter: f"config_{section}_{parameter}",
    file_paths=lambda section, parameter: [_get_config_file_path()]
)
def _cfg_read_impl(section: str, parameter: str) -> str:
    """
    Internal implementation of configuration reading (cached).
    
    This function is wrapped with memoization and file change detection.
    """
    config_file = _get_config_file_path()
    logger.debug("Reading configuration", section=section, parameter=parameter, 
                 config_file=config_file)
    
    try:
        # Validate config file exists
        config_path = Path(config_file)
        if not config_path.exists():
            logger.error("Configuration file not found", config_file=config_file)
            raise ConfigurationError(
                f"Configuration file not found: {config_file}",
                error_code="CONFIG_FILE_NOT_FOUND",
                context={'config_file': config_file}
            )
        
        # Read configuration
        config = configparser.ConfigParser()
        read_files = config.read(config_file)
        
        if not read_files:
            logger.error("Failed to read configuration file", config_file=config_file)
            raise ConfigurationError(
                f"Failed to read configuration file: {config_file}",
                error_code="CONFIG_READ_ERROR",
                context={'config_file': config_file}
            )
        
        # Validate section exists
        if section not in config:
            logger.error("Configuration section not found", section=section, 
                        available_sections=config.sections())
            raise ConfigurationError(
                f"Configuration section '{section}' not found in {config_file}. "
                f"Available sections: {', '.join(config.sections())}",
                error_code="CONFIG_SECTION_NOT_FOUND",
                context={'section': section, 'available_sections': config.sections()}
            )
        
        # Validate parameter exists
        if parameter not in config[section]:
            logger.error("Configuration parameter not found", section=section, 
                         parameter=parameter, available_params=list(config[section].keys()))
            raise ConfigurationError(
                f"Configuration parameter '{parameter}' not found in section '{section}' "
                f"of {config_file}. Available parameters: {', '.join(config[section].keys())}",
                error_code="CONFIG_PARAMETER_NOT_FOUND",
                context={
                    'section': section, 
                    'parameter': parameter,
                    'available_parameters': list(config[section].keys())
                }
            )
        
        value = config[section][parameter]
        logger.debug("Configuration read successfully", section=section, 
                     parameter=parameter, value_length=len(value))
        return value
        
    except ConfigurationError:
        # Re-raise configuration errors
        raise
    except configparser.Error as e:
        logger.error("Configuration parser error", section=section, parameter=parameter, 
                    error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Configuration parser error while reading {section}.{parameter} from {config_file}: {str(e)}",
            error_code="CONFIG_PARSER_ERROR",
            context={'section': section, 'parameter': parameter, 'error': str(e)}
        ) from e
    except Exception as e:
        logger.error("Unexpected error reading configuration", section=section, 
                    parameter=parameter, error=str(e), exc_info=True)
        raise ConfigurationError(
            f"Unexpected error reading configuration {section}.{parameter} from {config_file}: {str(e)}",
            error_code="CONFIG_UNEXPECTED_ERROR",
            context={'section': section, 'parameter': parameter, 'error': str(e)}
        ) from e


def cfg_read(section: str, parameter: str) -> str:
    """
    Read a configuration parameter from config.ini file (with caching).
    
    This function uses memoization with file change detection to cache
    configuration reads. The cache is automatically invalidated when the
    config file changes.
    
    Args:
        section: Configuration section name
        parameter: Configuration parameter name
        
    Returns:
        Configuration parameter value
        
    Raises:
        ConfigurationError: If config file not found, section/parameter missing,
                           or any other error occurs
    
    Example:
        >>> value = cfg_read('RULE', 'file_name')
        >>> value
        'data/input/rules_config_v4.json'
    """
    return _cfg_read_impl(section, parameter)
