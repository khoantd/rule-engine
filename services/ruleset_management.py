"""
RuleSet Management Service.

This module provides services for managing RuleSets, including CRUD operations.
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
from services.rule_management import get_rule_management_service
from domain.rules.ruleset_obj import RuleSet

logger = get_logger(__name__)


class RuleSetManagementService:
    """
    Service for managing RuleSets.
    
    This service provides operations for creating and managing RuleSets from
    existing rules and actions. RuleSets are logical groupings of rules.
    """
    
    def __init__(self, repository: Optional[ConfigRepository] = None):
        """
        Initialize ruleset management service.
        
        Args:
            repository: Optional configuration repository. If None, uses global repository.
        """
        self.repository = repository or get_config_repository()
        self.config_loader = get_config_loader()
        self.rule_service = get_rule_management_service()
        logger.debug("RuleSetManagementService initialized")
    
    def list_rulesets(self) -> List[Dict[str, Any]]:
        """
        List all rulesets.
        
        A RuleSet is a logical grouping of rules. This method creates RuleSet
        representations from the current rules configuration.
        
        Returns:
            List of ruleset dictionaries
        """
        logger.debug("Listing all rulesets")
        try:
            # Load all rules
            rules = self.rule_service.list_rules()
            
            # Load actions
            actions = self.config_loader.load_actions_set()
            
            # Create a default ruleset containing all rules
            ruleset = {
                "ruleset_name": "default",
                "rules": rules,
                "actionset": list(actions.keys()) if isinstance(actions, dict) else []
            }
            
            logger.info("Rulesets listed successfully", count=1)
            return [ruleset]
        except Exception as e:
            logger.error("Failed to list rulesets", error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to list rulesets: {str(e)}",
                error_code="RULESETS_LIST_ERROR",
                context={'error': str(e)}
            ) from e
    
    def get_ruleset(self, ruleset_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a ruleset by name.
        
        Args:
            ruleset_name: RuleSet name
            
        Returns:
            RuleSet dictionary if found, None otherwise
            
        Raises:
            DataValidationError: If ruleset_name is empty
        """
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty",
                error_code="RULESET_NAME_EMPTY"
            )
        
        logger.debug("Getting ruleset", ruleset_name=ruleset_name)
        try:
            rulesets = self.list_rulesets()
            for ruleset in rulesets:
                if ruleset.get("ruleset_name") == ruleset_name:
                    logger.info("RuleSet found", ruleset_name=ruleset_name)
                    return ruleset
            
            logger.warning("RuleSet not found", ruleset_name=ruleset_name)
            return None
        except Exception as e:
            logger.error("Failed to get ruleset", ruleset_name=ruleset_name, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to get ruleset {ruleset_name}: {str(e)}",
                error_code="RULESET_GET_ERROR",
                context={'ruleset_name': ruleset_name, 'error': str(e)}
            ) from e
    
    def create_ruleset(self, ruleset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new ruleset.
        
        Args:
            ruleset_data: RuleSet data dictionary. Must include:
                - ruleset_name: RuleSet name
                - rules: List of rule IDs or rule dictionaries
                - actionset: List of pattern strings or action dictionaries
                
        Returns:
            Created RuleSet dictionary
            
        Raises:
            DataValidationError: If ruleset data is invalid or ruleset name already exists
            ConfigurationError: If ruleset cannot be created
            
        Note:
            This is a logical operation. RuleSets are derived from rules and actions.
            The actual persistence is managed through rules and actions management.
        """
        logger.debug("Creating ruleset", ruleset_name=ruleset_data.get("ruleset_name"))
        
        # Validate required fields
        if "ruleset_name" not in ruleset_data:
            raise DataValidationError(
                "Missing required field: ruleset_name",
                error_code="RULESET_FIELD_MISSING",
                context={'field': 'ruleset_name'}
            )
        
        ruleset_name = ruleset_data["ruleset_name"]
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty",
                error_code="RULESET_NAME_EMPTY"
            )
        
        try:
            # Check if ruleset already exists
            existing_ruleset = self.get_ruleset(ruleset_name)
            if existing_ruleset:
                raise DataValidationError(
                    f"RuleSet with name '{ruleset_name}' already exists",
                    error_code="RULESET_NAME_EXISTS",
                    context={'ruleset_name': ruleset_name}
                )
            
            # Validate rules if provided
            rules = ruleset_data.get("rules", [])
            if isinstance(rules, list):
                # Validate rule IDs exist
                all_rules = self.rule_service.list_rules()
                rule_ids = {rule.get("id") for rule in all_rules}
                for rule_ref in rules:
                    if isinstance(rule_ref, str):
                        if rule_ref not in rule_ids:
                            raise DataValidationError(
                                f"Rule ID '{rule_ref}' not found",
                                error_code="RULE_ID_NOT_FOUND",
                                context={'rule_id': rule_ref}
                            )
                    elif isinstance(rule_ref, dict):
                        rule_id = rule_ref.get("id")
                        if rule_id and rule_id not in rule_ids:
                            raise DataValidationError(
                                f"Rule ID '{rule_id}' not found",
                                error_code="RULE_ID_NOT_FOUND",
                                context={'rule_id': rule_id}
                            )
            
            # Validate actions if provided
            actionset = ruleset_data.get("actionset", [])
            if isinstance(actionset, list):
                # Validate pattern strings exist
                all_actions = self.config_loader.load_actions_set()
                if isinstance(all_actions, dict):
                    for action_ref in actionset:
                        if isinstance(action_ref, str):
                            if action_ref not in all_actions:
                                raise DataValidationError(
                                    f"Action pattern '{action_ref}' not found",
                                    error_code="ACTION_PATTERN_NOT_FOUND",
                                    context={'pattern': action_ref}
                                )
            
            logger.info("RuleSet created successfully", ruleset_name=ruleset_name)
            return ruleset_data
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to create ruleset", ruleset_name=ruleset_name, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to create ruleset: {str(e)}",
                error_code="RULESET_CREATE_ERROR",
                context={'ruleset_name': ruleset_name, 'error': str(e)}
            ) from e
    
    def update_ruleset(self, ruleset_name: str, ruleset_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing ruleset.
        
        Args:
            ruleset_name: RuleSet name
            ruleset_data: Updated RuleSet data dictionary
            
        Returns:
            Updated RuleSet dictionary
            
        Raises:
            DataValidationError: If ruleset_name is empty or ruleset not found
            ConfigurationError: If ruleset cannot be updated
        """
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty",
                error_code="RULESET_NAME_EMPTY"
            )
        
        logger.debug("Updating ruleset", ruleset_name=ruleset_name)
        
        try:
            # Check if ruleset exists
            existing_ruleset = self.get_ruleset(ruleset_name)
            if not existing_ruleset:
                raise DataValidationError(
                    f"RuleSet with name '{ruleset_name}' not found",
                    error_code="RULESET_NOT_FOUND",
                    context={'ruleset_name': ruleset_name}
                )
            
            # Preserve name
            ruleset_data["ruleset_name"] = ruleset_name
            
            # Validate rules and actions (same as create)
            rules = ruleset_data.get("rules", [])
            if isinstance(rules, list):
                all_rules = self.rule_service.list_rules()
                rule_ids = {rule.get("id") for rule in all_rules}
                for rule_ref in rules:
                    if isinstance(rule_ref, str):
                        if rule_ref not in rule_ids:
                            raise DataValidationError(
                                f"Rule ID '{rule_ref}' not found",
                                error_code="RULE_ID_NOT_FOUND",
                                context={'rule_id': rule_ref}
                            )
            
            actionset = ruleset_data.get("actionset", [])
            if isinstance(actionset, list):
                all_actions = self.config_loader.load_actions_set()
                if isinstance(all_actions, dict):
                    for action_ref in actionset:
                        if isinstance(action_ref, str):
                            if action_ref not in all_actions:
                                raise DataValidationError(
                                    f"Action pattern '{action_ref}' not found",
                                    error_code="ACTION_PATTERN_NOT_FOUND",
                                    context={'pattern': action_ref}
                                )
            
            logger.info("RuleSet updated successfully", ruleset_name=ruleset_name)
            return ruleset_data
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to update ruleset", ruleset_name=ruleset_name, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to update ruleset: {str(e)}",
                error_code="RULESET_UPDATE_ERROR",
                context={'ruleset_name': ruleset_name, 'error': str(e)}
            ) from e
    
    def delete_ruleset(self, ruleset_name: str) -> None:
        """
        Delete a ruleset.
        
        Args:
            ruleset_name: RuleSet name
            
        Raises:
            DataValidationError: If ruleset_name is empty or ruleset not found
            ConfigurationError: If ruleset cannot be deleted
            
        Note:
            Since RuleSets are logical groupings, deletion is primarily a validation
            operation. The actual rules and actions remain unchanged.
        """
        if not ruleset_name or not ruleset_name.strip():
            raise DataValidationError(
                "RuleSet name cannot be empty",
                error_code="RULESET_NAME_EMPTY"
            )
        
        logger.debug("Deleting ruleset", ruleset_name=ruleset_name)
        
        try:
            # Check if ruleset exists
            existing_ruleset = self.get_ruleset(ruleset_name)
            if not existing_ruleset:
                raise DataValidationError(
                    f"RuleSet with name '{ruleset_name}' not found",
                    error_code="RULESET_NOT_FOUND",
                    context={'ruleset_name': ruleset_name}
                )
            
            logger.info("RuleSet deleted successfully", ruleset_name=ruleset_name)
            
        except DataValidationError:
            raise
        except Exception as e:
            logger.error("Failed to delete ruleset", ruleset_name=ruleset_name, error=str(e), exc_info=True)
            raise ConfigurationError(
                f"Failed to delete ruleset: {str(e)}",
                error_code="RULESET_DELETE_ERROR",
                context={'ruleset_name': ruleset_name, 'error': str(e)}
            ) from e


# Global service instance
_ruleset_management_service: Optional[RuleSetManagementService] = None


def get_ruleset_management_service() -> RuleSetManagementService:
    """
    Get the global ruleset management service instance.
    
    Returns:
        RuleSetManagementService instance
    """
    global _ruleset_management_service
    if _ruleset_management_service is None:
        _ruleset_management_service = RuleSetManagementService()
    return _ruleset_management_service

