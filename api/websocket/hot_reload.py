"""
WebSocket support for real-time rule reload notifications.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import json
import asyncio

from fastapi import WebSocket, WebSocketDisconnect, status as http_status

from common.logger import get_logger
from services.hot_reload import get_hot_reload_service
from common.rule_registry import get_rule_registry

logger = get_logger(__name__)


class ReloadNotificationManager:
    """
    Manages WebSocket connections for rule reload notifications.
    """

    def __init__(self):
        """Initialize notification manager."""
        self._active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

        # Subscribe to hot reload events
        hot_reload_service = get_hot_reload_service()
        hot_reload_service.subscribe(self._on_hot_reload_event)

        # Subscribe to registry events
        rule_registry = get_rule_registry()
        rule_registry.subscribe(self._on_registry_event)

        logger.info("ReloadNotificationManager initialized")

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()

        async with self._lock:
            self._active_connections.append(websocket)

        logger.info(
            "WebSocket client connected",
            client_count=len(self._active_connections),
        )

        # Send initial status
        await self.send_status(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        async with self._lock:
            if websocket in self._active_connections:
                self._active_connections.remove(websocket)

        logger.info(
            "WebSocket client disconnected",
            client_count=len(self._active_connections),
        )

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Broadcast an event to all connected clients.

        Args:
            event_type: Type of event
            data: Event data
        """
        message = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }

        disconnected_clients = []

        async with self._lock:
            for connection in self._active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(
                        "Failed to send WebSocket message",
                        error=str(e),
                    )
                    disconnected_clients.append(connection)

        # Remove disconnected clients
        for client in disconnected_clients:
            await self.disconnect(client)

    async def send_status(self, websocket: WebSocket) -> None:
        """
        Send current status to a WebSocket client.

        Args:
            websocket: WebSocket connection
        """
        hot_reload_service = get_hot_reload_service()
        rule_registry = get_rule_registry()

        status = {
            "event_type": "status",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "hot_reload": hot_reload_service.get_status(),
                "registry": rule_registry.get_stats(),
            },
        }

        try:
            await websocket.send_json(status)
        except Exception as e:
            logger.warning("Failed to send status", error=str(e))

    def _on_hot_reload_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Handle hot reload events.

        Args:
            event_type: Type of event
            data: Event data
        """
        # Broadcast to all WebSocket clients
        try:
            asyncio.create_task(self.broadcast(event_type, data))
        except Exception as e:
            logger.error(
                "Failed to broadcast hot reload event",
                event_type=event_type,
                error=str(e),
                exc_info=True,
            )

    def _on_registry_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Handle registry events.

        Args:
            event_type: Type of event
            data: Event data
        """
        # Broadcast to all WebSocket clients
        try:
            asyncio.create_task(self.broadcast(f"registry_{event_type}", data))
        except Exception as e:
            logger.error(
                "Failed to broadcast registry event",
                event_type=event_type,
                error=str(e),
                exc_info=True,
            )


# Global notification manager instance
_notification_manager: Optional[ReloadNotificationManager] = None


def get_notification_manager() -> ReloadNotificationManager:
    """
    Get global notification manager instance.

    Returns:
        ReloadNotificationManager instance
    """
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = ReloadNotificationManager()
    return _notification_manager
