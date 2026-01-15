#!/usr/bin/env python3
"""
Startup script for Rule Engine API web service.

Usage:
    python run_api.py
    
    Or with environment variables:
    API_HOST=0.0.0.0 API_PORT=8000 python run_api.py
    
    Or with API key authentication:
    API_KEY_ENABLED=true API_KEY=your-secret-key python run_api.py
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from common.config import get_config
from common.logger import get_logger

logger = get_logger(__name__)


def main():
    """Start the Rule Engine API server."""
    try:
        # Get configuration
        config = get_config()
        
        # Get server configuration from environment or defaults
        host = os.getenv('API_HOST', '0.0.0.0')
        port = int(os.getenv('API_PORT', '8000'))
        workers = int(os.getenv('API_WORKERS', '1'))
        log_level = config.log_level.lower()
        reload = config.is_development()
        
        # Log startup information
        logger.info("Starting Rule Engine API")
        logger.info("Configuration", environment=config.environment, host=host, port=port)
        
        api_key_enabled = os.getenv('API_KEY_ENABLED', 'false').lower() == 'true'
        if api_key_enabled:
            logger.info("API key authentication: ENABLED")
        else:
            logger.info("API key authentication: DISABLED")
        
        # Start uvicorn server
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            workers=workers if not reload else 1,  # Reload only works with 1 worker
            log_level=log_level,
            reload=reload,
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping server")
    except Exception as e:
        logger.error("Failed to start API server", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

