from typing import Dict, Set, Optional, Any
from datetime import datetime
import json
from fastapi import WebSocket

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
