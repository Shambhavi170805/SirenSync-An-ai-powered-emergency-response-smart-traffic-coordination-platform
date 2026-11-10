"""Optional consumer for Nidhi's emergency-scoped ambulance tracking WebSocket."""

import asyncio
import json
import os
from typing import Callable


class TrackingConsumer:
    """Subscribe to tracking events without importing or changing teammate code."""

    def __init__(self, on_event: Callable[[str, str, dict], None]):
        self.url = os.getenv("SIRENSYNC_TRACKING_WS_URL", "ws://127.0.0.1:8000/api/v1/tracking/ws")
        self.on_event = on_event
        self.tasks: dict[str, asyncio.Task] = {}
        self.status: dict[str, str] = {}

    async def subscribe(self, emergency_id: str, ambulance_id: str) -> None:
        old = self.tasks.get(emergency_id)
        if old and not old.done():
            old.cancel()
        self.tasks[emergency_id] = asyncio.create_task(
            self._consume(emergency_id, ambulance_id), name=f"tracking-{emergency_id}"
        )

    async def unsubscribe(self, emergency_id: str) -> None:
        task = self.tasks.pop(emergency_id, None)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.status[emergency_id] = "STOPPED"

    async def _consume(self, emergency_id: str, ambulance_id: str) -> None:
        try:
            import websockets
        except ImportError:
            self.status[emergency_id] = "DEPENDENCY_MISSING: install module requirements"
            return

        delay = 1
        while True:
            try:
                self.status[emergency_id] = "CONNECTING"
                async with websockets.connect(self.url, open_timeout=8, ping_interval=20) as socket:
                    await socket.send(json.dumps({"action": "subscribe", "emergency_id": emergency_id}))
                    self.status[emergency_id] = "CONNECTED"
                    delay = 1
                    async for raw in socket:
                        try:
                            message = json.loads(raw)
                        except (TypeError, json.JSONDecodeError):
                            continue
                        event_type = str(message.get("type") or "")
                        payload = message.get("payload") or {}
                        if event_type == "pong":
                            continue
                        incoming_emergency = payload.get("emergencyId") or payload.get("emergency_id")
                        incoming_ambulance = payload.get("ambulanceId") or payload.get("ambulance_id")
                        if incoming_emergency and incoming_emergency != emergency_id:
                            continue
                        if incoming_ambulance and incoming_ambulance != ambulance_id:
                            continue
                        if event_type in {"SNAPSHOT", "LOCATION_UPDATE", "ROUTE_PROGRESS_UPDATE", "STATUS_CHANGE"}:
                            self.on_event(event_type, emergency_id, payload)
                self.status[emergency_id] = "DISCONNECTED"
            except asyncio.CancelledError:
                self.status[emergency_id] = "STOPPED"
                raise
            except Exception as exc:
                self.status[emergency_id] = f"RETRYING: {type(exc).__name__}"
            await asyncio.sleep(delay)
            delay = min(delay * 2, 15)

    async def stop(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.tasks.clear()

    def snapshot(self) -> dict:
        return dict(self.status)
