"""
Rule Management Service.

This module provides services for managing Rules, including CRUD operations.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from common.logger import get_logger
from common.exceptions import (
    DataValidationError,
    ConfigurationError,
)
from common.repository.config_repository import get_config_repository, ConfigRepository
from common.config_loader import get_config_loader
from common.util import cfg_read
from common.json_util import read_json_file, create_json_file
from domain.rules.rule_obj import Rule, ExtRule

logger = get_logger(__name__)


class RuleManagementService:
    """
    Service for managing Rules.
    
    This service provides CRUD operations for Rules, including loading from
    and saving to configuration files.
    """
    
    def __init__(self, repository: Optional[ConfigRepository] = None):
        """
        Initialize rule management service.
        
        Args:
            repository: Optional configuration repository. If None, uses global repository.
        """
        self.repository = repository or get_config_repository()
        self.config_loader = get_config_loader()
        logger.debug("RuleManagementService initialized")
    
    def _get_rules_config_path(self) -> str:
        """
        Get the rules configuration file path.
        
        Returns:
            Path to rules configuration file
            
        Raises:
            ConfigurationError: If configuration cannot be read
        """
        try:
            config_file = cfg_read("RULE", "file_name")
            return config_file
        except Exception as e:
            logger.error("Failed to get rules config path", error=str(e))
            raise ConfigurationError(
                f"Failed to get rules configuration path: {str(e)}",
                error_code="CONFIG_PATH_ERROR",
                context={'error': str(e)}
            ) from e
    
    def _load_full_config(self) -> Dict[str, Any]:
        """
        Load the full rules configuration file.
        
        Returns:
            Complete configuration dictionary with rules_set and patterns
            
        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        try:
            config_file = self._get_rules_config_path()
            config_data = self.repository.read_json(config_file)
            
            # Ensure structure exists
            if not isinstance(config_data, dict):
                logger.warning("Invalid config structure, creating default")
                config_data = {"rules_set": [], "patterns": {}}
            elif "rules_set" not in config_data:
                config_data["rules_set"] = []
            elif "patterns" not in config_data:
                config_data["patterns"] = {}
            
            return config_data
        except Exception as e:
            logger.error("Failed to load rules configuration", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to load rules configuration: {str(e)}",
                error_code="RULES_CONFIG_LOAD_ERROR",
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
            config_file = self._get_rules_config_path()
            
            # For file-based repository, save directly
            if isinstance(self.repository, type(self.repository)) and hasattr(self.repository, '_resolve_path'):
                file_path = self.repository._resolve_path(config_file)
            else:
                # Default to relative path resolution
                file_path = config_file
            
            # Create directory if it doesn't exist
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Save using json_util
            create_json_file(config_data, file_path_obj.name, str(file_path_obj.parent))
            
            # Clear cache so changes are reflected
            self.config_loader.load_rules_set.cache_clear() if hasattr(self.config_loader.load_rules_set, 'cache_clear') else None
            self.config_loader.load_actions_set.cache_clear() if hasattr(self.config_loader.load_actions_set, 'cache_clear') else None
            
            logger.info("Rules configuration saved successfully", config_file=config_file)
        except Exception as e:
            logger.error("Failed to save rules configuration", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to save rules configuration: {str(e)}",
                error_code="RULES_CONFIG_SAVE_ERROR",
                context={'error': str(e)}
            ) from e
    
    def list_rules(self) -> List[Dict[str, Any]]:
        """
        List all rules.
        
        Returns:
            List of rule dictionaries
        """
        logger.debug("Listing all rules")
        try:
            rules = self.config_loader.load_rules_set()
            logger.info("Rules listed successfully", count=len(rules))
            return rules
        except Exception as e:
            logger.error("Failed to list rules", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list rules: {str(e)}",
                error_code="RULES_LIST_ERROR",
                context={'error': str(e)}
            ) from e
    
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a rule by ID.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Rule dictionary if found, None otherwise
            
        Raises:
            DataValidationError: If rule_id is empty
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty",
                error_code="RULE_ID_EMPTY"
            )
        
        logger.debug("Getting rule", rule_id=rule_id)
        try:
            rules = self.list_rules()
            for rule in rules:
                if rule.get("id") == rule_id:
                    logger.info("Rule found", rule_id=rule_id)
                    return rule
            
            logger.warning("Rule not found", rule_id=rule_id)
            return None
        except Exception as e:
            logger.error("Failed to get rule", rule_id=rule_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to get rule {rule_id}: {str(e)}",
                error_code="RULE_GET_ERROR",
                context={'rule_id': rule_id, 'error': str(e)}
            ) from e
    
    def create_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new rule.
        
        Args:
            rule_data: Rule data dictionary. Must include:
                - id: Unique rule identifier
                - rule_name: Rule name
                - conditions: Conditions dictionary
                - description: Rule description
                - result: Result string
                - Optional: rule_point, weight, priority, type, action_result
                
        Returns:
            Created rule dictionary
            
        Raises:
            DataValidationError: If rule data is invalid or rule ID already exists
            ConfigurationError: If rule cannot be created
        """
        logger.debug("Creating rule", rule_id=rule_data.get("id"))
        
        # Validate required fields
        required_fields = ["id", "rule_name", "conditions", "description", "result"]
        for field in required_fields:
            if field not in rule_data:
                raise DataValidationError(
                    f"Missing required field: {field}",
                    error_code="RULE_FIELD_MISSING",
                    context={'field': field}
                )
        
        rule_id = rule_data["id"]
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty",
                error_code="RULE_ID_EMPTY"
            )
        
        try:
            # Check if rule already exists
            existing_rule = self.get_rule(rule_id)
            if existing_rule:
                raise DataValidationError(
                    f"Rule with ID '{rule_id}' already exists",
                    error_code="RULE_ID_EXISTS",
                    context={'rule_id': rule_id}
                )
            
            # Load full config
            config_data = self._load_full_config()
            
            # Add new rule
            config_data["rules_set"].append(rule_data)
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Rule created successfully", rule_id=rule_id)
            return rule_data
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to create rule", rule_id=rule_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to create rule: {str(e)}",
                error_code="RULE_CREATE_ERROR",
                context={'rule_id': rule_id, 'error': str(e)}
            ) from e
    
    def update_rule(self, rule_id: str, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing rule.
        
        Args:
            rule_id: Rule identifier
            rule_data: Updated rule data dictionary
            
        Returns:
            Updated rule dictionary
            
        Raises:
            DataValidationError: If rule_id is empty or rule not found
            ConfigurationError: If rule cannot be updated
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty",
                error_code="RULE_ID_EMPTY"
            )
        
        logger.debug("Updating rule", rule_id=rule_id)
        
        try:
            # Load full config
            config_data = self._load_full_config()
            
            # Find and update rule
            rule_found = False
            for i, rule in enumerate(config_data["rules_set"]):
                if rule.get("id") == rule_id:
                    # Preserve ID
                    rule_data["id"] = rule_id
                    config_data["rules_set"][i] = rule_data
                    rule_found = True
                    break
            
            if not rule_found:
                raise DataValidationError(
                    f"Rule with ID '{rule_id}' not found",
                    error_code="RULE_NOT_FOUND",
                    context={'rule_id': rule_id}
                )
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Rule updated successfully", rule_id=rule_id)
            return rule_data
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to update rule", rule_id=rule_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to update rule: {str(e)}",
                error_code="RULE_UPDATE_ERROR",
                context={'rule_id': rule_id, 'error': str(e)}
            ) from e
    
    def delete_rule(self, rule_id: str) -> None:
        """
        Delete a rule.
        
        Args:
            rule_id: Rule identifier
            
        Raises:
            DataValidationError: If rule_id is empty or rule not found
            ConfigurationError: If rule cannot be deleted
        """
        if not rule_id or not rule_id.strip():
            raise DataValidationError(
                "Rule ID cannot be empty",
                error_code="RULE_ID_EMPTY"
            )
        
        logger.debug("Deleting rule", rule_id=rule_id)
        
        try:
            # Load full config
            config_data = self._load_full_config()
            
            # Store original count
            original_count = len(config_data["rules_set"])
            
            # Find and remove rule
            config_data["rules_set"] = [
                rule for rule in config_data["rules_set"]
                if rule.get("id") != rule_id
            ]
            
            # Check if rule was actually removed
            if len(config_data["rules_set"]) == original_count:
                raise DataValidationError(
                    f"Rule with ID '{rule_id}' not found",
                    error_code="RULE_NOT_FOUND",
                    context={'rule_id': rule_id}
                )
            
            # Save configuration
            self._save_config(config_data)
            
            logger.info("Rule deleted successfully", rule_id=rule_id)
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to delete rule", rule_id=rule_id, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to delete rule: {str(e)}",
                error_code="RULE_DELETE_ERROR",
                context={'rule_id': rule_id, 'error': str(e)}
            ) from e


# Global service instance
_rule_management_service: Optional[RuleManagementService] = None


def get_rule_management_service() -> RuleManagementService:
    """
    Get the global rule management service instance.
    
    Returns:
        RuleManagementService instance
    """
    global _rule_management_service
    if _rule_management_service is None:
        _rule_management_service = RuleManagementService()
    return _rule_management_service

