"""
Path normalization middleware for API requests.

Normalizes the request path by collapsing multiple consecutive slashes into one.
This ensures paths like //api/v1/rules/execute (e.g. from base URL + path concatenation)
match the registered route /api/v1/rules/execute and avoid 404s.
"""

import re
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from common.logger import get_logger

logger = get_logger(__name__)

# Collapse two or more slashes to one
_MULTI_SLASH = re.compile(r"/+")


def _normalize_path(path: str) -> str:
    """
    Normalize path by collapsing consecutive slashes to one and ensuring single leading slash.

    Args:
        path: Raw request path (e.g. "//api/v1/rules/execute").

    Returns:
        Normalized path (e.g. "/api/v1/rules/execute").
    """
    if not path:
        return "/"
    normalized = _MULTI_SLASH.sub("/", path)
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized


class PathNormalizerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that normalizes the request path before routing.

    Prevents 404s when clients send paths with duplicate slashes
    (e.g. base URL "http://host/" + "/api/v1/rules/execute").
    """

    async def dispatch(self, request: Request, call_next):
        """Normalize path in scope and pass request to next handler."""
        path = request.scope.get("path", "")
        normalized = _normalize_path(path)
        if normalized != path:
            request.scope["path"] = normalized
            logger.debug(
                "Path normalized for routing",
                original_path=path,
                normalized_path=normalized,
                correlation_id=getattr(request.state, "correlation_id", None),
            )
        return await call_next(request)
