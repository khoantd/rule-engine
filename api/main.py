"""
Main FastAPI application for Rule Engine web service.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request as StarletteRequest

from api.routes import (
    rules,
    workflow,
    health,
    rules_management,
    conditions_management,
    actions_management,
    rulesets_management,
    dmn_upload
)
from api.middleware.logging import LoggingMiddleware
from api.middleware.auth import AuthenticationMiddleware
from api.middleware.errors import exception_handler, validation_exception_handler
from common.logger import get_logger
from common.config import get_config
import os

logger = get_logger(__name__)

# Get configuration
config = get_config()

# Create FastAPI application
app = FastAPI(
    title="Rule Engine API",
    description="REST API for executing business rules and workflows",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add authentication middleware (if enabled)
api_key_enabled = os.getenv('API_KEY_ENABLED', 'false').lower() == 'true'
if api_key_enabled:
    logger.info("API key authentication enabled")
    app.add_middleware(AuthenticationMiddleware)
else:
    logger.info("API key authentication disabled")

# Register exception handlers
async def fastapi_exception_handler(request: StarletteRequest, exc: Exception):
    """Wrapper for FastAPI exception handler."""
    return await exception_handler(request, exc)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, fastapi_exception_handler)
app.add_exception_handler(Exception, fastapi_exception_handler)

# Include routers
app.include_router(health.router)
app.include_router(rules.router)
app.include_router(workflow.router)

# Include management routers
app.include_router(rules_management.router)
app.include_router(conditions_management.router)
app.include_router(actions_management.router)
app.include_router(rulesets_management.router)

# Include DMN upload router
app.include_router(dmn_upload.router)


@app.on_event("startup")
async def startup_event():
    """Execute on application startup."""
    logger.info("Rule Engine API starting up", environment=config.environment)
    logger.info("API documentation available at /docs")
    logger.info("Health check available at /health")


@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown."""
    logger.info("Rule Engine API shutting down")


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8000'))
    log_level = config.log_level.lower()
    
    logger.info(f"Starting Rule Engine API on {host}:{port}")
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=config.is_development()
    )

