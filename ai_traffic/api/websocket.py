"""
WebSocket Connection Manager.
Broadcasts real-time detection, signal state transitions, and corridor progress
events to connected client dashboards and upstream services.
"""

import asyncio
from typing import Any, Dict, List
from fastapi import WebSocket, WebSocketDisconnect

from ai_traffic.core.logger import logger


class WebSocketManager:
    """
    Maintains active WebSocket subscriber connections.
    """

    def __init__(self):
        self._connections: List[WebSocket] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(f"[WEBSOCKET] Client connected. Total active clients: {len(self._connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
            logger.info(f"[WEBSOCKET] Client disconnected. Total active clients: {len(self._connections)}")

    async def broadcast_async(self, message: Dict[str, Any]) -> None:
        disconnected = []
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Thread-safe broadcast helper that can be called from worker threads.
        """
        if not self._connections:
            return

        try:
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast_async(message), self._loop)
            else:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.broadcast_async(message), loop)
        except Exception as e:
            logger.debug(f"[WEBSOCKET] Broadcast scheduling error: {e}")


# Singleton instance
ws_manager = WebSocketManager()
