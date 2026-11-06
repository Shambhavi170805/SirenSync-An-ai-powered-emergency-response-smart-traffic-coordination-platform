import asyncio
import concurrent.futures
from typing import Dict, Set, Optional, Any
from datetime import datetime
import json
import logging
import threading
from fastapi import WebSocket

logger = logging.getLogger("sirensync.tracking")

class TrackingConnectionManager:
    """
    In-memory WebSocket connection manager for real-time ambulance telemetry & status streaming.
    Supports:
    - Channel subscriptions by emergency_id
    - Global broadcast channel for hospital operations / evaluators
    - Graceful disconnect cleanup
    - Message broadcast fan-out
    """

    def __init__(self):
        # Maps emergency_id -> set of active WebSockets
        self._emergency_channels: Dict[str, Set[WebSocket]] = {}
        # Global listeners (e.g. hospital dashboard, evaluator screens)
        self._global_listeners: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()

    def set_event_loop(self, loop: Optional[asyncio.AbstractEventLoop]) -> None:
        """Registers or clears the primary application asyncio event loop in a thread-safe manner."""
        with self._lock:
            self._loop = loop

    def broadcast_event_threadsafe(
        self,
        event_type: str,
        payload: Dict[str, Any],
        emergency_id: Optional[str] = None
    ) -> None:
        """
        Thread-safe broadcast scheduling helper.
        Safely dispatches broadcast_event() to the application event loop from either
        the main async loop or synchronous worker threads.
        Never blocks caller and never raises exceptions to calling transaction.
        """
        coro = self.broadcast_event(event_type=event_type, payload=payload, emergency_id=emergency_id)

        # Retrieve registered application loop under thread-safety lock
        with self._lock:
            app_loop = self._loop

        # Check if caller has a running event loop
        current_loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        # Case A: Caller has a running event loop
        if current_loop is not None:
            # Schedule directly only if caller loop is the registered application loop and running
            if app_loop is not None and current_loop is app_loop and app_loop.is_running():
                try:
                    task = app_loop.create_task(coro)
                    task.add_done_callback(self._handle_task_result)
                    return
                except Exception as e:
                    logger.warning(f"[TrackingHub] Failed to schedule broadcast task on application loop: {e}")
                    coro.close()
                    return
            else:
                # Caller has a foreign loop or app_loop is not running; do not access sockets across loops
                logger.warning(
                    "[TrackingHub] Caller event loop does not match registered application loop. "
                    "Skipping broadcast to prevent cross-loop socket access."
                )
                coro.close()
                return

        # Case B: Caller is in a synchronous worker thread (no running loop); schedule onto registered app loop
        if app_loop is not None and app_loop.is_running() and not app_loop.is_closed():
            try:
                future = asyncio.run_coroutine_threadsafe(coro, app_loop)
                future.add_done_callback(self._handle_future_result)
                return
            except Exception as e:
                logger.warning(f"[TrackingHub] Failed to dispatch coroutine to registered application loop: {e}")
                coro.close()
                return

        # Case C: No usable application event loop exists (e.g. standalone test execution or shutdown)
        logger.warning(
            f"[TrackingHub] No active application event loop registered for broadcast '{event_type}'. "
            "Telemetry broadcast skipped safely."
        )
        coro.close()

    @staticmethod
    def _handle_task_result(task: asyncio.Task) -> None:
        """Callback to log exceptions from asyncio Tasks without raising unhandled errors."""
        try:
            if not task.cancelled():
                exc = task.exception()
                if exc:
                    logger.warning(f"[TrackingHub] Broadcast task error: {exc}")
        except Exception as e:
            logger.warning(f"[TrackingHub] Error inspecting task completion: {e}")

    @staticmethod
    def _handle_future_result(future: concurrent.futures.Future) -> None:
        """Callback to log exceptions from cross-thread Futures without blocking or crashing."""
        try:
            if not future.cancelled():
                exc = future.exception()
                if exc:
                    logger.warning(f"[TrackingHub] Cross-thread broadcast future error: {exc}")
        except Exception as e:
            logger.warning(f"[TrackingHub] Error inspecting future completion: {e}")

    async def connect(self, websocket: WebSocket, emergency_id: Optional[str] = None):
        """Accepts a WebSocket connection and registers it to the appropriate channel."""
        await websocket.accept()
        if emergency_id and emergency_id.lower() != "all":
            self.subscribe(websocket, emergency_id)
        else:
            self._global_listeners.add(websocket)

    def disconnect(self, websocket: WebSocket, emergency_id: Optional[str] = None):
        """Removes a closed or errored WebSocket from all active channels and global listeners."""
        empty_channels = []
        for ch_id, ch_set in self._emergency_channels.items():
            ch_set.discard(websocket)
            if not ch_set:
                empty_channels.append(ch_id)
        for empty_id in empty_channels:
            del self._emergency_channels[empty_id]
        self._global_listeners.discard(websocket)

    def subscribe(self, websocket: WebSocket, emergency_id: str):
        """Subscribes an existing connection to a specific emergency channel or global stream."""
        if emergency_id.lower() == "all":
            # Remove from all emergency channels when switching to global listening
            empty_channels = []
            for ch_id, ch_set in self._emergency_channels.items():
                ch_set.discard(websocket)
                if not ch_set:
                    empty_channels.append(ch_id)
            for empty_id in empty_channels:
                del self._emergency_channels[empty_id]
            self._global_listeners.add(websocket)
            return

        # Emergency-scoped subscription: remove from global listeners so it does not
        # receive broadcasts for unrelated emergencies
        self._global_listeners.discard(websocket)

        # Remove from any other emergency channels if switching
        empty_channels = []
        for ch_id, ch_set in self._emergency_channels.items():
            if ch_id != emergency_id:
                ch_set.discard(websocket)
                if not ch_set:
                    empty_channels.append(ch_id)
        for empty_id in empty_channels:
            del self._emergency_channels[empty_id]

        if emergency_id not in self._emergency_channels:
            self._emergency_channels[emergency_id] = set()
        self._emergency_channels[emergency_id].add(websocket)

    async def broadcast_event(self, event_type: str, payload: Dict[str, Any], emergency_id: Optional[str] = None):
        """
        Broadcasts a typed event payload to subscribers of the specified emergency_id
        as well as global listeners.
        """
        message = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        raw_msg = json.dumps(message, default=str)

        # 1. Send to emergency-specific subscribers
        targets: Set[WebSocket] = set()
        if emergency_id and emergency_id in self._emergency_channels:
            targets.update(self._emergency_channels[emergency_id])

        # 2. Include global listeners
        targets.update(self._global_listeners)

        dead_sockets = []
        for ws in targets:
            try:
                await ws.send_text(raw_msg)
            except Exception:
                dead_sockets.append(ws)

        # Cleanup disconnected sockets across all channels and global listeners
        for dead_ws in dead_sockets:
            self.disconnect(dead_ws)

# Singleton tracking hub instance
tracking_hub = TrackingConnectionManager()
