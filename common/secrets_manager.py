"""
Secrets management module for Rule Engine.

This module provides secure secrets management with support for:
- AWS Systems Manager Parameter Store
- AWS Secrets Manager
- Environment variables (for development)
- Secure secret retrieval and caching
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from common.exceptions import ConfigurationError, SecurityError
from common.logger import get_logger

logger = get_logger(__name__)


class SecretsManager:
    """
    Manages secrets retrieval from various sources.
    
    Supports:
    - AWS Systems Manager Parameter Store
    - AWS Secrets Manager
    - Environment variables (fallback for development)
    
    Priority order:
    1. AWS SSM Parameter Store (if enabled and available)
    2. AWS Secrets Manager (if enabled and available)
    3. Environment variables (fallback)
    """
    
    def __init__(
        self,
        use_ssm: bool = False,
        use_secrets_manager: bool = False,
        ssm_prefix: str = '/rule-engine/',
        secrets_manager_prefix: str = 'rule-engine/',
        region_name: Optional[str] = None
    ):
        """
        Initialize Secrets Manager.
        
        Args:
            use_ssm: Whether to use AWS Systems Manager Parameter Store
            use_secrets_manager: Whether to use AWS Secrets Manager
            ssm_prefix: Prefix for SSM parameters (e.g., '/rule-engine/')
            secrets_manager_prefix: Prefix for Secrets Manager secrets
            region_name: AWS region name (defaults to environment or us-east-1)
        """
        self.use_ssm = use_ssm and BOTO3_AVAILABLE
        self.use_secrets_manager = use_secrets_manager and BOTO3_AVAILABLE
        self.ssm_prefix = ssm_prefix.rstrip('/')
        self.secrets_manager_prefix = secrets_manager_prefix.rstrip('/')
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize AWS clients if needed
        self._ssm_client = None
        self._secrets_client = None
        
        if self.use_ssm:
            try:
                self._ssm_client = boto3.client('ssm', region_name=self.region_name)
                logger.info("SSM client initialized", region=self.region_name)
            except Exception as e:
                logger.warning("Failed to initialize SSM client", error=str(e))
                self.use_ssm = False
        
        if self.use_secrets_manager:
            try:
                self._secrets_client = boto3.client('secretsmanager', region_name=self.region_name)
                logger.info("Secrets Manager client initialized", region=self.region_name)
            except Exception as e:
                logger.warning("Failed to initialize Secrets Manager client", error=str(e))
                self.use_secrets_manager = False
    
    def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        """
        Get a secret value by key.
        
        Retrieves secrets in priority order:
        1. AWS SSM Parameter Store (if enabled)
        2. AWS Secrets Manager (if enabled)
        3. Environment variables (fallback)
        
        Args:
            key: Secret key name (e.g., 'jira_token', 'api_key')
            required: If True, raises error if secret not found. If False, returns None.
        
        Returns:
            Secret value as string, or None if not found and required=False
        
        Raises:
            SecurityError: If secret is required but not found
            ConfigurationError: If AWS service errors occur
        
        Example:
            >>> manager = SecretsManager(use_ssm=True)
            >>> token = manager.get_secret('jira_token')
            >>> # Returns value from SSM or environment
        """
        logger.debug("Retrieving secret", key=key, use_ssm=self.use_ssm, 
                    use_secrets_manager=self.use_secrets_manager)
        
        # Try SSM Parameter Store first
        if self.use_ssm and self._ssm_client:
            try:
                ssm_key = f"{self.ssm_prefix}/{key}"
                response = self._ssm_client.get_parameter(
                    Name=ssm_key,
                    WithDecryption=True
                )
                value = response['Parameter']['Value']
                logger.info("Secret retrieved from SSM", key=key, ssm_key=ssm_key)
                return value
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'ParameterNotFound':
                    logger.debug("Secret not found in SSM", key=key, ssm_key=ssm_key)
                    # Continue to next source
                else:
                    logger.error("SSM error retrieving secret", key=key, 
                               error_code=error_code, error=str(e))
                    raise ConfigurationError(
                        f"Failed to retrieve secret '{key}' from SSM: {error_code} - {str(e)}",
                        error_code="SSM_SECRET_ERROR",
                        context={'key': key, 'error_code': error_code}
                    ) from e
            except Exception as e:
                logger.error("Unexpected error retrieving secret from SSM", key=key, error=str(e))
                # Fall through to next source
        
        # Try Secrets Manager
        if self.use_secrets_manager and self._secrets_client:
            try:
                secret_name = f"{self.secrets_manager_prefix}/{key}"
                response = self._secrets_client.get_secret_value(SecretId=secret_name)
                value = response['SecretString']
                logger.info("Secret retrieved from Secrets Manager", key=key, secret_name=secret_name)
                return value
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'ResourceNotFoundException':
                    logger.debug("Secret not found in Secrets Manager", key=key, secret_name=secret_name)
                    # Continue to next source
                else:
                    logger.error("Secrets Manager error retrieving secret", key=key, 
                               error_code=error_code, error=str(e))
                    raise ConfigurationError(
                        f"Failed to retrieve secret '{key}' from Secrets Manager: {error_code} - {str(e)}",
                        error_code="SECRETS_MANAGER_ERROR",
                        context={'key': key, 'error_code': error_code}
                    ) from e
            except Exception as e:
                logger.error("Unexpected error retrieving secret from Secrets Manager", 
                           key=key, error=str(e))
                # Fall through to environment variables
        
        # Fallback to environment variables
        env_key = key.upper().replace('-', '_')
        value = os.getenv(env_key)
        
        if value:
            logger.debug("Secret retrieved from environment", key=key, env_key=env_key)
            return value
        
        # Secret not found
        if required:
            logger.error("Required secret not found", key=key, checked_locations=[
                'SSM Parameter Store' if self.use_ssm else None,
                'Secrets Manager' if self.use_secrets_manager else None,
                'Environment Variables'
            ])
            raise SecurityError(
                f"Required secret '{key}' not found in any configured source",
                error_code="SECRET_NOT_FOUND",
                context={'key': key, 'checked_locations': [
                    loc for loc in [
                        'SSM Parameter Store' if self.use_ssm else None,
                        'Secrets Manager' if self.use_secrets_manager else None,
                        'Environment Variables'
                    ] if loc
                ]}
            )
        
        logger.debug("Optional secret not found", key=key)
        return None
    
    def get_secrets_batch(self, keys: list, required: bool = True) -> Dict[str, Optional[str]]:
        """
        Get multiple secrets at once.
        
        Args:
            keys: List of secret keys to retrieve
            required: If True, raises error if any required secret not found
        
        Returns:
            Dictionary mapping keys to secret values
        
        Raises:
            SecurityError: If any required secret is not found
        """
        secrets = {}
        missing_keys = []
        
        for key in keys:
            try:
                secrets[key] = self.get_secret(key, required=required)
            except SecurityError:
                if required:
                    missing_keys.append(key)
                secrets[key] = None
        
        if missing_keys and required:
            raise SecurityError(
                f"Required secrets not found: {', '.join(missing_keys)}",
                error_code="SECRETS_NOT_FOUND",
                context={'missing_keys': missing_keys}
            )
        
        return secrets


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Get global secrets manager instance.
    
    Returns:
        SecretsManager instance initialized from environment/config
    """
    global _secrets_manager
    
    if _secrets_manager is None:
        use_ssm = os.getenv('USE_SSM', 'false').lower() == 'true'
        use_secrets_manager = os.getenv('USE_SECRETS_MANAGER', 'false').lower() == 'true'
        ssm_prefix = os.getenv('SSM_PREFIX', '/rule-engine/')
        secrets_manager_prefix = os.getenv('SECRETS_MANAGER_PREFIX', 'rule-engine/')
        region_name = os.getenv('AWS_REGION', 'us-east-1')
        
        _secrets_manager = SecretsManager(
            use_ssm=use_ssm,
            use_secrets_manager=use_secrets_manager,
            ssm_prefix=ssm_prefix,
            secrets_manager_prefix=secrets_manager_prefix,
            region_name=region_name
        )
        
        logger.info("Global secrets manager initialized", 
                   use_ssm=use_ssm, use_secrets_manager=use_secrets_manager)
    
    return _secrets_manager


def set_secrets_manager(manager: SecretsManager) -> None:
    """
    Set global secrets manager instance (useful for testing).
    
    Args:
        manager: SecretsManager instance to set
    """
    global _secrets_manager
    _secrets_manager = manager
    logger.debug("Global secrets manager instance set")

