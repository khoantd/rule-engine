import os
import boto3
from typing import Optional
from botocore.exceptions import ClientError, BotoCoreError
from common.logger import get_logger
from common.exceptions import StorageError
from common.security import validate_s3_key

logger = get_logger(__name__)


def aws_s3_config_file_read(bucket: str, config_file: str) -> str:
    """
    Read a configuration file from AWS S3 bucket securely.
    
    This function creates an S3 client, validates the S3 key to prevent path injection,
    retrieves the specified object from the bucket, and returns its contents as a decoded string.
    
    Args:
        bucket: Name of the S3 bucket containing the configuration file.
            Bucket must be accessible with current AWS credentials.
        config_file: S3 key/path to the configuration file within the bucket.
            Example: "config/rules_config.json" or "rules_config.json"
            The key will be validated to prevent path injection attacks.
    
    Returns:
        File contents as a decoded string. File encoding is assumed to be UTF-8.
    
    Raises:
        SecurityError: If S3 key contains dangerous patterns
        StorageError: If:
            - S3 client cannot be created
            - Bucket does not exist or is not accessible
            - File does not exist at the specified key
            - File cannot be read or decoded
            - Any AWS service error occurs
    
    Example:
        >>> content = aws_s3_config_file_read('my-bucket', 'config/rules.json')
        >>> len(content)
        1024
    """
    logger.info("Reading configuration file from S3", bucket=bucket, config_file=config_file)
    
    # Validate S3 key to prevent path injection
    try:
        validate_s3_key(config_file)
    except Exception as e:
        # Re-raise security errors as-is
        raise
    
    try:
        s3_boto = boto3.client('s3')
        logger.debug("S3 client created successfully")
        obj = s3_boto.get_object(Bucket=bucket, Key=config_file)
        content = obj['Body'].read().decode('utf-8')
        logger.info("Configuration file read successfully from S3", bucket=bucket, 
                   config_file=config_file, content_length=len(content))
        return content
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error("AWS S3 client error", bucket=bucket, config_file=config_file, 
                    error_code=error_code, error=str(e), exc_info=True)
        raise StorageError(
            f"Failed to read config file {config_file} from bucket {bucket}: {error_code} - {str(e)}"
        ) from e
    except BotoCoreError as e:
        logger.error("AWS S3 core error", bucket=bucket, config_file=config_file, 
                    error=str(e), exc_info=True)
        raise StorageError(
            f"Failed to read config file {config_file} from bucket {bucket}: {str(e)}"
        ) from e
    except Exception as e:
        logger.error("Failed to read configuration file from S3", bucket=bucket, 
                    config_file=config_file, error=str(e), exc_info=True)
        raise StorageError(
            f"Failed to read config file {config_file} from bucket {bucket}: {str(e)}"
        ) from e


# Constants for S3 configuration
# Note: In production, bucket name should come from environment variables or config
# DEPRECATED: Use Config class from common.config instead
def _get_s3_bucket() -> str:
    """
    Get S3 bucket name from configuration.
    
    This function uses the Config class to get the S3 bucket name,
    falling back to environment variable or default for backward compatibility.
    
    Returns:
        S3 bucket name
    """
    try:
        from common.config import get_config
        config = get_config()
        if config.s3_bucket:
            return config.s3_bucket
    except Exception:
        pass
    
    # Fallback to environment variable or default
    return os.getenv('S3_BUCKET_RULE_CONFIG', os.getenv('S3_BUCKET', 'rule-config-file'))

S3_BUCKET_RULE_CONFIG: str = _get_s3_bucket()  # Legacy constant for backward compatibility

def config_file_read(location: str, config_file: str) -> str:
    """
    Read a configuration file from specified location securely.
    
    This function is a dispatcher that reads configuration files from
    different storage locations. Currently supports S3 storage.
    All paths are validated to prevent path injection attacks.
    
    Args:
        location: Storage location type. Currently only "S3" is supported.
            Future support for "LOCAL", "GCS", etc. may be added.
        config_file: File path/key within the storage location.
            For S3: S3 key (e.g., "config/rules.json") - will be validated
            For local: file path (not yet implemented)
    
    Returns:
        File contents as a decoded string.
    
    Raises:
        SecurityError: If S3 key contains dangerous patterns
        StorageError: If:
            - Location type is not supported
            - S3 read fails (see aws_s3_config_file_read for details)
            - Any other storage error occurs
    
    Example:
        >>> content = config_file_read('S3', 'config/rules.json')
        >>> len(content)
        1024
    """
    logger.info("Reading configuration file", location=location, config_file=config_file)
    
    # Validate S3 key before processing
    if location == "S3":
        try:
            validate_s3_key(config_file)
        except Exception as e:
            # Re-raise security errors as-is
            raise
        
        # Get bucket from configuration (environment variable or config)
        try:
            from common.config import get_config
            config = get_config()
            bucket = config.s3_bucket or os.getenv('S3_BUCKET_RULE_CONFIG', 'rule-config-file')
        except Exception:
            # Fallback to environment variable or default
            bucket = os.getenv('S3_BUCKET_RULE_CONFIG', os.getenv('S3_BUCKET', 'rule-config-file'))
        logger.debug("Using S3 location", bucket=bucket)
        obj = aws_s3_config_file_read(bucket, config_file)
        return obj
    else:
        logger.warning("Unsupported location type", location=location)
        raise StorageError(
            f"Unsupported location type: {location}. Supported locations: S3",
            error_code="UNSUPPORTED_LOCATION",
            context={'location': location, 'config_file': config_file}
        )
