"""
Main FastAPI application for Rule Engine web service.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request as StarletteRequest

from api.middleware.auth import AuthenticationMiddleware
from api.middleware.errors import exception_handler, validation_exception_handler
from api.middleware.logging import LoggingMiddleware
from api.middleware.path_normalizer import PathNormalizerMiddleware
from api.routers import register_routers, register_websocket_routes
from common.config import get_config
from common.logger import get_logger

logger = get_logger(__name__)
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Rule Engine API starting up", environment=config.environment)
    logger.info("API documentation available at /docs")
    logger.info("Health check available at /health")
    yield
    logger.info("Rule Engine API shutting down")


# Create FastAPI application
app = FastAPI(
    title="Rule Engine API",
    description="REST API for executing business rules and workflows",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(PathNormalizerMiddleware)

api_key_enabled = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
if api_key_enabled:
    logger.info("API key authentication enabled")
    app.add_middleware(AuthenticationMiddleware)
else:
    logger.info("API key authentication disabled")


async def fastapi_exception_handler(request: StarletteRequest, exc: Exception):
    """Wrapper for FastAPI exception handler."""
    return await exception_handler(request, exc)


app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, fastapi_exception_handler)
app.add_exception_handler(Exception, fastapi_exception_handler)

register_routers(app)
register_websocket_routes(app)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    log_level = config.log_level.lower()

    logger.info("Starting Rule Engine API on %s:%s", host, port)

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=config.is_development(),
    )
