from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from backend.database.session import get_db, SessionLocal
from backend.schemas.ambulance import TrackingSnapshotResponse
from backend.services.ambulance_service import AmbulanceDispatchService
from backend.services.tracking_service import tracking_hub
import json

router = APIRouter(prefix="/tracking", tags=["Real-Time Tracking & Telemetry Hub"])

@router.get("/snapshot/{emergency_id}", response_model=TrackingSnapshotResponse)
def get_tracking_snapshot_endpoint(
    emergency_id: str,
    db: Session = Depends(get_db)
):
    """
    REST Fallback Snapshot Endpoint.
    Returns complete current telemetry and operational state for the specified emergency.
    Used for initial page loads, reconnect recovery, and consumers unable to open WebSockets.
    """
    snapshot = AmbulanceDispatchService.get_tracking_snapshot(db=db, emergency_id=emergency_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active ambulance tracking snapshot available for emergency '{emergency_id}'."
        )
    return snapshot

@router.websocket("/ws")
async def websocket_tracking_endpoint(websocket: WebSocket):
    """
    Real-Time WebSocket Tracking Stream.
    Allows clients (driver UI, patient screen, hospital triage desk, traffic AI)
    to receive live location updates, route progress, status transitions, and reroute alerts.

    Protocol:
    - On Connect: client can send {"action": "subscribe", "emergency_id": "emg-xxx"}
    - Immediate Response: full state snapshot is pushed to the client for reconnection recovery.
    - Heartbeat: client can send {"action": "ping"} -> server responds {"type": "pong"}
    """
    current_emergency_id = None
    await tracking_hub.connect(websocket, emergency_id="all")

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
                action = msg.get("action")

                if action == "subscribe":
                    emg_id = msg.get("emergency_id")
                    if emg_id:
                        current_emergency_id = emg_id
                        tracking_hub.subscribe(websocket, emg_id)

                        # Provide immediate state snapshot for reconnect recovery
                        db = SessionLocal()
                        try:
                            snapshot = AmbulanceDispatchService.get_tracking_snapshot(db=db, emergency_id=emg_id)
                            if snapshot:
                                await websocket.send_text(json.dumps({
                                    "type": "SNAPSHOT",
                                    "payload": snapshot.model_dump(mode="json")
                                }, default=str))
                        finally:
                            db.close()

                elif action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        tracking_hub.disconnect(websocket, emergency_id=current_emergency_id)
    except Exception:
        tracking_hub.disconnect(websocket, emergency_id=current_emergency_id)
