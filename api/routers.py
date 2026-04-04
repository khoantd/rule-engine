"""
Register HTTP and WebSocket routes on the FastAPI application.

Centralizes router inclusion so ``api.main`` stays a thin composition root.
"""

from typing import List

from fastapi import APIRouter, FastAPI

from api.routes import (
    ab_testing,
    actions_management,
    attributes_management,
    conditions_management,
    consumers,
    dmn_upload,
    health,
    hot_reload,
    rule_versioning,
    rules,
    rules_management,
    rulesets_management,
    workflow,
    workflows,
)
from api.websocket.hot_reload import hot_reload_websocket_endpoint


def get_api_routers() -> List[APIRouter]:
    """Ordered API routers (prefixes and matching order preserved)."""
    return [
        health.router,
        rules.router,
        workflow.router,
        workflows.router,
        rules_management.router,
        conditions_management.router,
        attributes_management.router,
        actions_management.router,
        rulesets_management.router,
        dmn_upload.router,
        rule_versioning.router,
        ab_testing.router,
        hot_reload.router,
        consumers.router,
    ]


def register_routers(app: FastAPI) -> None:
    """Include all HTTP routers on ``app``."""
    for router in get_api_routers():
        app.include_router(router)


def register_websocket_routes(app: FastAPI) -> None:
    """Register WebSocket endpoints on ``app``."""
    app.websocket("/ws/hot-reload")(hot_reload_websocket_endpoint)
