"""
Authentication middleware for API requests.
"""

from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from common.logger import get_logger
from common.config import get_config
import os

logger = get_logger(__name__)

# API Key security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Extract API key from request header.
    
    Args:
        api_key: API key from header
        
    Returns:
        API key string or None
        
    Raises:
        HTTPException: If API key authentication is required but not provided
    """
    config = get_config()
    
    # Check if API key authentication is enabled
    api_key_enabled = os.getenv('API_KEY_ENABLED', 'false').lower() == 'true'
    expected_api_key = os.getenv('API_KEY')
    
    # If API key auth is not enabled, allow all requests
    if not api_key_enabled:
        logger.debug("API key authentication disabled, allowing request")
        return api_key
    
    # If API key auth is enabled but no key configured, allow in dev only
    if not expected_api_key:
        if config.is_development():
            logger.warning("API key authentication enabled but no API key configured, allowing in dev")
            return api_key
        else:
            logger.error("API key authentication enabled but no API key configured in production")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key authentication misconfigured"
            )
    
    # Validate API key
    if not api_key:
        logger.warning("API key authentication required but no API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key != expected_api_key:
        logger.warning("Invalid API key provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    logger.debug("API key authentication successful")
    return api_key


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    
    This middleware can be optionally enabled via environment variables:
    - API_KEY_ENABLED=true (default: false)
    - API_KEY=<your-api-key> (required if API_KEY_ENABLED=true)
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request through authentication middleware."""
        # Skip authentication for health check and docs endpoints
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            response = await call_next(request)
            return response
        
        # Check if API key auth is enabled
        api_key_enabled = os.getenv('API_KEY_ENABLED', 'false').lower() == 'true'
        
        if api_key_enabled:
            try:
                # Try to get and validate API key
                api_key = request.headers.get("X-API-Key")
                get_api_key(api_key)
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                logger.error("Authentication middleware error", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication error"
                )
        
        response = await call_next(request)
        return response

