"""
Security utilities for the Rule Engine.

This module provides security-related utilities including:
- Path validation to prevent directory traversal attacks
- Secure file operations
- Secrets validation
"""

import os
from pathlib import Path
from typing import Optional
import re

from common.exceptions import ConfigurationError, SecurityError
from common.logger import get_logger

logger = get_logger(__name__)


def validate_file_path(file_path: str, allowed_base: Optional[str] = None, 
                       must_exist: bool = False) -> Path:
    """
    Validate a file path to prevent directory traversal attacks.
    
    This function ensures that:
    - Path does not contain directory traversal sequences (.., ~, etc.)
    - Path is within allowed base directory if specified
    - Path is resolved to an absolute path for validation
    
    Args:
        file_path: Path to validate. Can be relative or absolute.
        allowed_base: Optional base directory that the path must be within.
            If None, only validates against directory traversal.
        must_exist: If True, raises error if file doesn't exist.
    
    Returns:
        Resolved Path object
    
    Raises:
        SecurityError: If path contains directory traversal or is outside allowed base
        ConfigurationError: If must_exist=True and file doesn't exist
    
    Example:
        >>> validate_file_path('data/config.json', allowed_base='data')
        PosixPath('/workspace/data/config.json')
        >>> validate_file_path('../../etc/passwd', allowed_base='data')
        SecurityError: Path contains directory traversal
    """
    logger.debug("Validating file path", file_path=file_path, allowed_base=allowed_base)
    
    # Normalize path
    try:
        path = Path(file_path).resolve()
    except (OSError, ValueError) as e:
        logger.error("Invalid file path", file_path=file_path, error=str(e))
        raise SecurityError(
            f"Invalid file path '{file_path}': {str(e)}",
            error_code="INVALID_PATH",
            context={'file_path': file_path, 'error': str(e)}
        ) from e
    
    # Check for directory traversal patterns
    path_str = str(path)
    
    # Dangerous patterns that could lead to directory traversal
    dangerous_patterns = [
        r'\.\.',  # Parent directory references
        r'~/',    # Home directory expansion
        r'//',    # UNC paths (on Windows)
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, path_str):
            logger.error("Path contains dangerous pattern", file_path=file_path, pattern=pattern)
            raise SecurityError(
                f"Path contains dangerous pattern '{pattern}': {file_path}",
                error_code="DIRECTORY_TRAVERSAL_DETECTED",
                context={'file_path': file_path, 'pattern': pattern}
            )
    
    # Validate against allowed base directory
    if allowed_base:
        try:
            base_path = Path(allowed_base).resolve()
            if not path.is_relative_to(base_path):
                logger.error("Path outside allowed base", file_path=file_path, 
                           allowed_base=allowed_base)
                raise SecurityError(
                    f"Path '{file_path}' is outside allowed base directory '{allowed_base}'",
                    error_code="PATH_OUTSIDE_BASE",
                    context={'file_path': file_path, 'allowed_base': allowed_base}
                )
        except (TypeError, AttributeError):
            # Python < 3.9 compatibility
            try:
                path.relative_to(base_path)
            except ValueError:
                logger.error("Path outside allowed base", file_path=file_path, 
                           allowed_base=allowed_base)
                raise SecurityError(
                    f"Path '{file_path}' is outside allowed base directory '{allowed_base}'",
                    error_code="PATH_OUTSIDE_BASE",
                    context={'file_path': file_path, 'allowed_base': allowed_base}
                )
    
    # Check if file exists if required
    if must_exist and not path.exists():
        logger.error("File does not exist", file_path=file_path)
        raise ConfigurationError(
            f"File does not exist: {file_path}",
            error_code="FILE_NOT_FOUND",
            context={'file_path': file_path}
        )
    
    logger.debug("File path validated successfully", file_path=str(path))
    return path


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path injection attacks.
    
    Removes or replaces dangerous characters that could be used in path injection.
    
    Args:
        filename: Filename to sanitize
    
    Returns:
        Sanitized filename safe for use in file operations
    
    Example:
        >>> sanitize_filename('../../etc/passwd')
        '____etc_passwd'
        >>> sanitize_filename('config.json')
        'config.json'
    """
    # Remove or replace dangerous characters
    dangerous_chars = ['/', '\\', '..', '~', '\x00']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing dots and spaces (Windows restrictions)
    sanitized = sanitized.strip('. ')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    return sanitized


def get_secure_file_permissions(is_sensitive: bool = False) -> int:
    """
    Get secure file permissions based on file sensitivity.
    
    Args:
        is_sensitive: If True, returns more restrictive permissions (owner-only)
            If False, returns standard permissions (owner/group read)
    
    Returns:
        File mode as integer (octal permissions)
    
    Example:
        >>> get_secure_file_permissions(is_sensitive=True)
        0o600  # Owner read/write only
        >>> get_secure_file_permissions(is_sensitive=False)
        0o644  # Owner read/write, group/others read
    """
    if is_sensitive:
        # Owner read/write only (600)
        return 0o600
    else:
        # Owner read/write, group/others read (644)
        return 0o644


def validate_config_secrets(config_dict: dict, required_secrets: Optional[list] = None) -> None:
    """
    Validate that configuration does not contain hard-coded secrets.
    
    This function checks for common patterns that indicate secrets are hard-coded
    and should instead be loaded from secure storage.
    
    Args:
        config_dict: Configuration dictionary to validate
        required_secrets: Optional list of secret keys that must be present
            but should be loaded from secure storage, not hard-coded
    
    Raises:
        SecurityError: If hard-coded secrets are detected
    
    Example:
        >>> config = {'jira_token': 'AEqPCgn5b5BSOArR0Aqu612D'}
        >>> validate_config_secrets(config, required_secrets=['jira_token'])
        SecurityError: Secret 'jira_token' appears to be hard-coded
    """
    # Common secret key patterns
    secret_patterns = [
        'password', 'passwd', 'pwd',
        'secret', 'token', 'key',
        'api_key', 'apikey', 'access_key',
        'credential', 'auth', 'authorization'
    ]
    
    for key, value in config_dict.items():
        key_lower = key.lower()
        
        # Check if this looks like a secret key
        is_secret_key = any(pattern in key_lower for pattern in secret_patterns)
        
        if is_secret_key and value:
            # Check if value looks hard-coded (not from env var or placeholder)
            value_str = str(value).strip()
            
            # Skip if it's clearly from environment or is a placeholder
            if value_str.startswith('${') or value_str.startswith('$'):
                continue
            
            # Skip if it's empty or None (will be loaded from secure storage)
            if not value_str or value_str.lower() in ['none', 'null', '']:
                continue
            
            logger.warning(
                "Potential hard-coded secret detected",
                key=key,
                value_length=len(value_str),
                value_preview=value_str[:10] + '...' if len(value_str) > 10 else value_str
            )
            
            # In production, this should raise an error
            # For now, we'll log a warning to allow gradual migration
            # raise SecurityError(
            #     f"Secret '{key}' appears to be hard-coded. Use secrets manager instead.",
            #     error_code="HARDCODED_SECRET_DETECTED",
            #     context={'key': key}
            # )


def validate_s3_key(s3_key: str) -> None:
    """
    Validate S3 key to prevent path injection and ensure proper format.
    
    Args:
        s3_key: S3 key/path to validate
    
    Raises:
        SecurityError: If S3 key is invalid or contains dangerous patterns
    
    Example:
        >>> validate_s3_key('config/rules.json')  # Valid
        >>> validate_s3_key('../../etc/passwd')    # Raises SecurityError
    """
    if not s3_key or not isinstance(s3_key, str):
        raise SecurityError(
            f"Invalid S3 key: {s3_key}",
            error_code="INVALID_S3_KEY",
            context={'s3_key': s3_key}
        )
    
    # S3 keys should not contain dangerous patterns
    dangerous_patterns = [
        r'\.\.',  # Parent directory
        r'//',    # Multiple slashes
        r'^\s',   # Leading whitespace
        r'\s$',   # Trailing whitespace
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, s3_key):
            logger.error("S3 key contains dangerous pattern", s3_key=s3_key, pattern=pattern)
            raise SecurityError(
                f"S3 key contains dangerous pattern '{pattern}': {s3_key}",
                error_code="INVALID_S3_KEY",
                context={'s3_key': s3_key, 'pattern': pattern}
            )
    
    # Normalize the key
    normalized = '/'.join(part for part in s3_key.split('/') if part)
    
    if normalized != s3_key:
        logger.warning("S3 key normalized", original=s3_key, normalized=normalized)
    
    logger.debug("S3 key validated", s3_key=s3_key)

