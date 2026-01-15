"""
Actions Management Service.

This module provides services for managing Actions/Patterns, including CRUD operations.
"""

from typing import Any, Dict, Optional

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.config_repository import get_config_repository, ConfigRepository
from common.config_loader import get_config_loader
from common.util import cfg_read
from common.json_util import create_json_file
from pathlib import Path

logger = get_logger(__name__)


class ActionsManagementService:
    """
    Service for managing Actions/Patterns.
    
    This service provides CRUD operations for Actions (patterns), including loading from
    and saving to configuration files.
    """
    
    def __init__(self, repository: Optional[ConfigRepository] = None):
        """
        Initialize actions management service.
        
        Args:
            repository: Optional configuration repository. If None, uses global repository.
        """
        self.repository = repository or get_config_repository()
        self.config_loader = get_config_loader()
        logger.debug("ActionsManagementService initialized")
    
    def _get_actions_config_path(self) -> str:
        """
        Get the actions/patterns configuration file path.
        
        Returns:
            Path to rules configuration file (patterns are in rules config)
            
        Raises:
            ConfigurationError: If configuration cannot be read
        """
        try:
            config_file = cfg_read("RULE", "file_name")
            return config_file
        except Exception as e:
            logger.error("Failed to get actions config path", error=str(e))
            raise ConfigurationError(
                f"Failed to get actions configuration path: {str(e)}",
                error_code="CONFIG_PATH_ERROR",
                context={'error': str(e)}
            ) from e
    
    def _load_full_config(self) -> Dict[str, Any]:
        """
        Load the full rules configuration file (which contains patterns).
        
        Returns:
            Complete configuration dictionary with rules_set and patterns
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        try:
            config_file = self._get_actions_config_path()
            config_data = self.repository.read_json(config_file)
            
            # Ensure structure exists
            if not isinstance(config_data, dict):
                logger.warning("Invalid config structure, creating default")
                config_data = {"rules_set": [], "patterns": {}}
            elif "patterns" not in config_data:
                config_data["patterns"] = {}
            elif "rules_set" not in config_data:
                config_data["rules_set"] = []
            
            return config_data
        except Exception as e:
            logger.error("Failed to load actions configuration", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to load actions configuration: {str(e)}",
                error_code="ACTIONS_CONFIG_LOAD_ERROR",
                context={'error': str(e)}
            ) from e
    
    def _save_config(self, config_data: Dict[str, Any]) -> None:
        """
        Save configuration data to file.
        
        Args:
            config_data: Configuration dictionary to save
            
        Raises:
            ConfigurationError: If configuration cannot be saved
        """
        try:
            config_file = self._get_actions_config_path()
            
            # For file-based repository, resolve path
            if hasattr(self.repository, '_resolve_path'):
                file_path = self.repository._resolve_path(config_file)
            else:
                file_path = config_file
            
            # Create directory if it doesn't exist
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Save using json_util
            create_json_file(config_data, file_path_obj.name, str(file_path_obj.parent))
            
            # Clear cache so changes are reflected
            if hasattr(self.config_loader.load_actions_set, 'cache_clear'):
                self.config_loader.load_actions_set.cache_clear()
            
            logger.info("Actions configuration saved successfully", config_file=config_file)
        except Exception as e:
            logger.error("Failed to save actions configuration", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to save actions configuration: {str(e)}",
                error_code="ACTIONS_CONFIG_SAVE_ERROR",
                context={'error': str(e)}
            ) from e
    
    def list_actions(self) -> Dict[str, Any]:
        """
        List all actions/patterns.
        
        Returns:
            Dictionary mapping pattern strings to action recommendations
        """
        logger.debug("Listing all actions")
        try:
            actions = self.config_loader.load_actions_set()
            logger.info("Actions listed successfully", count=len(actions))
            return actions
        except Exception as e:
            logger.error("Failed to list actions", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list actions: {str(e)}",
                error_code="ACTIONS_LIST_ERROR",
                context={'error': str(e)}
            ) from e
    
    def get_action(self, pattern: str) -> Optional[str]:
        """
        Get an action by pattern.
        
        Args:
            pattern: Pattern string (e.g., "YYY", "Y--")
            
        Returns:
            Action recommendation if found, None otherwise
            
        Raises:
            DataValidationError: If pattern is empty
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty",
                error_code="PATTERN_EMPTY"
            )
        
        logger.debug("Getting action", pattern=pattern)
        try:
            actions = self.list_actions()
            action = actions.get(pattern)
            if action:
                logger.info("Action found", pattern=pattern)
                return action
            
            logger.warning("Action not found", pattern=pattern)
            return None
        except Exception as e:
            logger.error("Failed to get action", pattern=pattern, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to get action {pattern}: {str(e)}",
                error_code="ACTION_GET_ERROR",
                context={'pattern': pattern, 'error': str(e)}
            ) from e
    
    def create_action(self, pattern: str, message: str) -> Dict[str, str]:
        """
        Create a new action/pattern.
        
        Args:
            pattern: Pattern string (e.g., "YYY", "Y--")
            message: Action recommendation message
            
        Returns:
            Created action dictionary with pattern and message
            
        Raises:
            DataValidationError: If pattern or message is empty, or pattern already exists
            ConfigurationError: If action cannot be created
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty",
                error_code="PATTERN_EMPTY"
            )
        
        if not message or not message.strip():
            raise DataValidationError(
                "Message cannot be empty",
                error_code="MESSAGE_EMPTY"
            )
        
        logger.debug("Creating action", pattern=pattern)
        
        try:
            # Check if action already exists
            existing_action = self.get_action(pattern)
            if existing_action:
                raise DataValidationError(
                    f"Action with pattern '{pattern}' already exists",
                    error_code="PATTERN_EXISTS",
                    context={'pattern': pattern}
                )
            
            # Load full config
            config_data = self._load_full_config()
            
            # Add new action
            config_data["patterns"][pattern] = message
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Action created successfully", pattern=pattern)
            return {pattern: message}
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to create action", pattern=pattern, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to create action: {str(e)}",
                error_code="ACTION_CREATE_ERROR",
                context={'pattern': pattern, 'error': str(e)}
            ) from e
    
    def update_action(self, pattern: str, message: str) -> Dict[str, str]:
        """
        Update an existing action/pattern.
        
        Args:
            pattern: Pattern string
            message: Updated action recommendation message
            
        Returns:
            Updated action dictionary with pattern and message
            
        Raises:
            DataValidationError: If pattern is empty, message is empty, or pattern not found
            ConfigurationError: If action cannot be updated
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty",
                error_code="PATTERN_EMPTY"
            )
        
        if not message or not message.strip():
            raise DataValidationError(
                "Message cannot be empty",
                error_code="MESSAGE_EMPTY"
            )
        
        logger.debug("Updating action", pattern=pattern)
        
        try:
            # Load full config
            config_data = self._load_full_config()
            
            # Check if pattern exists
            if pattern not in config_data["patterns"]:
                raise DataValidationError(
                    f"Action with pattern '{pattern}' not found",
                    error_code="PATTERN_NOT_FOUND",
                    context={'pattern': pattern}
                )
            
            # Update action
            config_data["patterns"][pattern] = message
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Action updated successfully", pattern=pattern)
            return {pattern: message}
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to update action", pattern=pattern, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to update action: {str(e)}",
                error_code="ACTION_UPDATE_ERROR",
                context={'pattern': pattern, 'error': str(e)}
            ) from e
    
    def delete_action(self, pattern: str) -> None:
        """
        Delete an action/pattern.
        
        Args:
            pattern: Pattern string
            
        Raises:
            DataValidationError: If pattern is empty or pattern not found
            ConfigurationError: If action cannot be deleted
        """
        if not pattern or not pattern.strip():
            raise DataValidationError(
                "Pattern cannot be empty",
                error_code="PATTERN_EMPTY"
            )
        
        logger.debug("Deleting action", pattern=pattern)
        
        try:
            # Load full config
            config_data = self._load_full_config()
            
            # Check if pattern exists
            if pattern not in config_data["patterns"]:
                raise DataValidationError(
                    f"Action with pattern '{pattern}' not found",
                    error_code="PATTERN_NOT_FOUND",
                    context={'pattern': pattern}
                )
            
            # Remove action
            del config_data["patterns"][pattern]
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Action deleted successfully", pattern=pattern)
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to delete action", pattern=pattern, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to delete action: {str(e)}",
                error_code="ACTION_DELETE_ERROR",
                context={'pattern': pattern, 'error': str(e)}
            ) from e


# Global service instance
_actions_management_service: Optional[ActionsManagementService] = None


def get_actions_management_service() -> ActionsManagementService:
    """
    Get the global actions management service instance.
    
    Returns:
        ActionsManagementService instance
    """
    global _actions_management_service
    if _actions_management_service is None:
        _actions_management_service = ActionsManagementService()
    return _actions_management_service

