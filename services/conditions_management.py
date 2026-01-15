"""
Conditions Management Service.

This module provides services for managing Conditions, including CRUD operations.
"""

from typing import Any, Dict, List, Optional

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.config_repository import get_config_repository, ConfigRepository
from common.config_loader import get_config_loader
from common.util import cfg_read
from common.json_util import create_json_file
from domain.conditions.condition_obj import Condition

logger = get_logger(__name__)


class ConditionsManagementService:
    """
    Service for managing Conditions.
    
    This service provides CRUD operations for Conditions, including loading from
    and saving to configuration files.
    """
    
    def __init__(self, repository: Optional[ConfigRepository] = None):
        """
        Initialize conditions management service.
        
        Args:
            repository: Optional configuration repository. If None, uses global repository.
        """
        self.repository = repository or get_config_repository()
        self.config_loader = get_config_loader()
        logger.debug("ConditionsManagementService initialized")
    
    def _get_conditions_config_path(self) -> str:
        """
        Get the conditions configuration file path.
        
        Returns:
            Path to conditions configuration file
            
        Raises:
            ConfigurationError: If configuration cannot be read
        """
        try:
            config_file = cfg_read("CONDITIONS", "file_name")
            return config_file
        except Exception as e:
            logger.error("Failed to get conditions config path", error=str(e))
            raise ConfigurationError(
                f"Failed to get conditions configuration path: {str(e)}",
                error_code="CONFIG_PATH_ERROR",
                context={'error': str(e)}
            ) from e
    
    def _load_full_config(self) -> Dict[str, Any]:
        """
        Load the full conditions configuration file.
        
        Returns:
            Complete configuration dictionary with conditions_set
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        try:
            config_file = self._get_conditions_config_path()
            config_data = self.repository.read_json(config_file)
            
            # Ensure structure exists
            if not isinstance(config_data, dict):
                logger.warning("Invalid config structure, creating default")
                config_data = {"conditions_set": []}
            elif "conditions_set" not in config_data:
                config_data["conditions_set"] = []
            
            return config_data
        except Exception as e:
            logger.error("Failed to load conditions configuration", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to load conditions configuration: {str(e)}",
                error_code="CONDITIONS_CONFIG_LOAD_ERROR",
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
            config_file = self._get_conditions_config_path()
            
            # For file-based repository, resolve path
            if hasattr(self.repository, '_resolve_path'):
                file_path = self.repository._resolve_path(config_file)
            else:
                file_path = config_file
            
            # Create directory if it doesn't exist
            from pathlib import Path
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Save using json_util
            create_json_file(config_data, file_path_obj.name, str(file_path_obj.parent))
            
            # Clear cache so changes are reflected
            if hasattr(self.config_loader.load_conditions_set, 'cache_clear'):
                self.config_loader.load_conditions_set.cache_clear()
            
            logger.info("Conditions configuration saved successfully", config_file=config_file)
        except Exception as e:
            logger.error("Failed to save conditions configuration", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to save conditions configuration: {str(e)}",
                error_code="CONDITIONS_CONFIG_SAVE_ERROR",
                context={'error': str(e)}
            ) from e
    
    def list_conditions(self) -> List[Dict[str, Any]]:
        """
        List all conditions.
        
        Returns:
            List of condition dictionaries
        """
        logger.debug("Listing all conditions")
        try:
            conditions = self.config_loader.load_conditions_set()
            logger.info("Conditions listed successfully", count=len(conditions))
            return conditions
        except Exception as e:
            logger.error("Failed to list conditions", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list conditions: {str(e)}",
                error_code="CONDITIONS_LIST_ERROR",
                context={'error': str(e)}
            ) from e
    
    def get_condition(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a condition by ID.
        
        Args:
            condition_id: Condition identifier
            
        Returns:
            Condition dictionary if found, None otherwise
            
        Raises:
            DataValidationError: If condition_id is empty
        """
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty",
                error_code="CONDITION_ID_EMPTY"
            )
        
        logger.debug("Getting condition", condition_id=condition_id)
        try:
            conditions = self.list_conditions()
            for condition in conditions:
                if condition.get("condition_id") == condition_id:
                    logger.info("Condition found", condition_id=condition_id)
                    return condition
            
            logger.warning("Condition not found", condition_id=condition_id)
            return None
        except Exception as e:
            logger.error("Failed to get condition", condition_id=condition_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to get condition {condition_id}: {str(e)}",
                error_code="CONDITION_GET_ERROR",
                context={'condition_id': condition_id, 'error': str(e)}
            ) from e
    
    def create_condition(self, condition_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new condition.
        
        Args:
            condition_data: Condition data dictionary. Must include:
                - condition_id: Unique condition identifier
                - condition_name: Condition name
                - attribute: Attribute name to check
                - equation: Equation operator
                - constant: Comparison value
                
        Returns:
            Created condition dictionary
            
        Raises:
            DataValidationError: If condition data is invalid or condition ID already exists
            ConfigurationError: If condition cannot be created
        """
        logger.debug("Creating condition", condition_id=condition_data.get("condition_id"))
        
        # Validate required fields
        required_fields = ["condition_id", "condition_name", "attribute", "equation", "constant"]
        for field in required_fields:
            if field not in condition_data:
                raise DataValidationError(
                    f"Missing required field: {field}",
                    error_code="CONDITION_FIELD_MISSING",
                    context={'field': field}
                )
        
        condition_id = condition_data["condition_id"]
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty",
                error_code="CONDITION_ID_EMPTY"
            )
        
        try:
            # Check if condition already exists
            existing_condition = self.get_condition(condition_id)
            if existing_condition:
                raise DataValidationError(
                    f"Condition with ID '{condition_id}' already exists",
                    error_code="CONDITION_ID_EXISTS",
                    context={'condition_id': condition_id}
                )
            
            # Load full config
            config_data = self._load_full_config()
            
            # Add new condition
            config_data["conditions_set"].append(condition_data)
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Condition created successfully", condition_id=condition_id)
            return condition_data
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to create condition", condition_id=condition_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to create condition: {str(e)}",
                error_code="CONDITION_CREATE_ERROR",
                context={'condition_id': condition_id, 'error': str(e)}
            ) from e
    
    def update_condition(self, condition_id: str, condition_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing condition.
        
        Args:
            condition_id: Condition identifier
            condition_data: Updated condition data dictionary
            
        Returns:
            Updated condition dictionary
            
        Raises:
            DataValidationError: If condition_id is empty or condition not found
            ConfigurationError: If condition cannot be updated
        """
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty",
                error_code="CONDITION_ID_EMPTY"
            )
        
        logger.debug("Updating condition", condition_id=condition_id)
        
        try:
            # Load full config
            config_data = self._load_full_config()
            
            # Find and update condition
            condition_found = False
            for i, condition in enumerate(config_data["conditions_set"]):
                if condition.get("condition_id") == condition_id:
                    # Preserve ID
                    condition_data["condition_id"] = condition_id
                    config_data["conditions_set"][i] = condition_data
                    condition_found = True
                    break
            
            if not condition_found:
                raise DataValidationError(
                    f"Condition with ID '{condition_id}' not found",
                    error_code="CONDITION_NOT_FOUND",
                    context={'condition_id': condition_id}
                )
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Condition updated successfully", condition_id=condition_id)
            return condition_data
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to update condition", condition_id=condition_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to update condition: {str(e)}",
                error_code="CONDITION_UPDATE_ERROR",
                context={'condition_id': condition_id, 'error': str(e)}
            ) from e
    
    def delete_condition(self, condition_id: str) -> None:
        """
        Delete a condition.
        
        Args:
            condition_id: Condition identifier
            
        Raises:
            DataValidationError: If condition_id is empty or condition not found
            ConfigurationError: If condition cannot be deleted
        """
        if not condition_id or not condition_id.strip():
            raise DataValidationError(
                "Condition ID cannot be empty",
                error_code="CONDITION_ID_EMPTY"
            )
        
        logger.debug("Deleting condition", condition_id=condition_id)
        
        try:
            # Load full config
            config_data = self._load_full_config()
            
            # Store original count
            original_count = len(config_data["conditions_set"])
            
            # Find and remove condition
            config_data["conditions_set"] = [
                condition for condition in config_data["conditions_set"]
                if condition.get("condition_id") != condition_id
            ]
            
            # Check if condition was actually removed
            if len(config_data["conditions_set"]) == original_count:
                raise DataValidationError(
                    f"Condition with ID '{condition_id}' not found",
                    error_code="CONDITION_NOT_FOUND",
                    context={'condition_id': condition_id}
                )
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Condition deleted successfully", condition_id=condition_id)
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to delete condition", condition_id=condition_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to delete condition: {str(e)}",
                error_code="CONDITION_DELETE_ERROR",
                context={'condition_id': condition_id, 'error': str(e)}
            ) from e


# Global service instance
_conditions_management_service: Optional[ConditionsManagementService] = None


def get_conditions_management_service() -> ConditionsManagementService:
    """
    Get the global conditions management service instance.
    
    Returns:
        ConditionsManagementService instance
    """
    global _conditions_management_service
    if _conditions_management_service is None:
        _conditions_management_service = ConditionsManagementService()
    return _conditions_management_service

