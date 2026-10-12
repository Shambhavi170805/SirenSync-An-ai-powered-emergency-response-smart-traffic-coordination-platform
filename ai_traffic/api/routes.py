"""
FastAPI Route Handlers for SirenSync AI-Traffic Module.
Exposes REST endpoints and WebSocket feeds for Patient Intake, Hospital Dashboard,
and Traffic Engineering modules.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from ai_traffic.api.schemas import (
    HealthResponse,
    JunctionStatusResponse,
    RouteInputRequest,
    RouteProgressUpdateRequest,
)
from ai_traffic.api.websocket import ws_manager
from ai_traffic.core.config import AppSettings, get_settings
from ai_traffic.core.database import get_db
from ai_traffic.core.logger import logger

router = APIRouter()

# Global module runtime references (injected by main.py during startup)
_runtime_context: Dict[str, Any] = {}


def set_runtime_context(context: Dict[str, Any]) -> None:
    global _runtime_context
    _runtime_context = context


def get_context() -> Dict[str, Any]:
    return _runtime_context


# ==============================================================================
# REST ENDPOINTS
# ==============================================================================

@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Returns system operational health, connected cameras, detector mode, and controller status.
    """
    ctx = get_context()
    settings: AppSettings = ctx.get("settings", get_settings())
    stream_mgr = ctx.get("stream_manager")
    detector = ctx.get("detector")
    controller = ctx.get("controller")
    route_mgr = ctx.get("route_manager")

    cam_statuses = stream_mgr.get_all_statuses() if stream_mgr else {}
    ctrl_info = controller.get_adapter_info() if controller else {}
    is_custom_weights = detector.is_custom_model if detector else False
    active_routes = len(route_mgr.get_all_routes()) if route_mgr else 0

    return HealthResponse(
        status="HEALTHY",
        app=settings.name,
        version=settings.version,
        environment=settings.environment,
        controller_type=settings.signal_controller_type,
        controller_info=ctrl_info,
        cameras=cam_statuses,
        detector_custom_weights_loaded=is_custom_weights,
        active_routes_count=active_routes,
        timestamp=ctx.get("start_time", "")
    )


@router.get("/junctions", response_model=List[JunctionStatusResponse])
def get_junctions() -> List[JunctionStatusResponse]:
    """
    Returns current signal phase, pre-emption status, and queue depth for each junction.
    """
    ctx = get_context()
    state_machine = ctx.get("state_machine")
    settings: AppSettings = ctx.get("settings", get_settings())

    if not state_machine:
        return []

    states = state_machine.get_all_junction_states()
    junction_map = {j.junction_id: j for j in settings.junctions}

    result = []
    for s in states:
        if not s:
            continue
        j_cfg = junction_map.get(s["junction_id"])
        result.append(JunctionStatusResponse(
            junction_id=s["junction_id"],
            name=j_cfg.name if j_cfg else s["junction_id"],
            lat=j_cfg.lat if j_cfg else None,
            lng=j_cfg.lng if j_cfg else None,
            state=s["state"],
            active_ambulance_id=s.get("active_ambulance_id"),
            reason=s.get("reason"),
            seconds_in_state=s.get("seconds_in_state"),
            last_event_time=s.get("last_event_time"),
            queued_ambulances=s.get("queued_ambulances", [])
        ))

    return result


@router.get("/events")
def get_events(
    limit: int = Query(default=50, ge=1, le=500),
    junction_id: Optional[str] = None,
    event_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns historical traffic and pre-emption events from persistent storage.
    """
    db = get_db()
    return db.get_events(limit=limit, junction_id=junction_id, event_type=event_type)


@router.post("/route")
def post_route(request: RouteInputRequest) -> Dict[str, Any]:
    """
    Ingests an ambulance transit corridor from upstream ambulance coordination module.
    Optionally fetches route points from Google Maps Directions API if origin/destination provided.
    """
    ctx = get_context()
    route_mgr = ctx.get("route_manager")
    gmaps_client = ctx.get("gmaps_client")
    settings: AppSettings = ctx.get("settings", get_settings())

    if not route_mgr:
        raise HTTPException(status_code=500, detail="Route manager not initialized")

    points: List[Dict[str, float]] = []

    # If route points are already provided, convert to dictionaries
    if request.route_points:
        points = [{"lat": p.lat, "lng": p.lng} for p in request.route_points]
    elif request.origin and request.destination and gmaps_client:
        # Query Google Maps Directions API
        g_route = gmaps_client.get_route(request.origin, request.destination)
        points = g_route.get("points", [])

    if not points:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'route_points' or valid 'origin' and 'destination'"
        )

    # If junction list was not explicitly specified, map all configured junctions along the corridor
    junctions = request.junctions
    if not junctions:
        junctions = [j.junction_id for j in settings.junctions]

    route_data = route_mgr.ingest_route(
        ambulance_id=request.ambulance_id,
        route_points=points,
        junctions_on_route=junctions,
        progress_percent=request.progress_percent,
        emergency_severity=request.emergency_severity
    )

    return {
        "status": "INGESTED",
        "ambulance_id": request.ambulance_id,
        "junctions_registered": junctions,
        "points_count": len(points),
        "route_summary": route_data
    }


@router.post("/route/progress")
def update_route_progress(request: RouteProgressUpdateRequest) -> Dict[str, Any]:
    """
    Receives live GPS breadcrumbs and transit progress percentage from upstream tracking.
    """
    ctx = get_context()
    route_mgr = ctx.get("route_manager")
    if not route_mgr:
        raise HTTPException(status_code=500, detail="Route manager not initialized")

    updated = route_mgr.update_progress(
        ambulance_id=request.ambulance_id,
        progress_percent=request.progress_percent,
        current_lat=request.current_lat,
        current_lng=request.current_lng
    )

    if not updated:
        raise HTTPException(status_code=404, detail=f"Active route '{request.ambulance_id}' not found")

    return {"status": "UPDATED", "progress_percent": request.progress_percent}


@router.get("/routes")
def get_routes() -> List[Dict[str, Any]]:
    """
    Returns all active ambulance routes being managed.
    """
    ctx = get_context()
    route_mgr = ctx.get("route_manager")
    return route_mgr.get_all_routes() if route_mgr else []


@router.get("/video_feed/{camera_id}")
def video_feed(camera_id: str):
    """
    Streams live annotated MJPEG video for the given camera source.
    """
    ctx = get_context()
    stream_mgr = ctx.get("stream_manager")
    if not stream_mgr:
        raise HTTPException(status_code=500, detail="Stream manager not active")

    return StreamingResponse(
        stream_mgr.generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.post("/demo/simulate")
def trigger_demo_simulation() -> Dict[str, Any]:
    """
    Dispatches a demo ambulance scenario: loads sample route and triggers camera approach.
    """
    ctx = get_context()
    stream_mgr = ctx.get("stream_manager")
    route_mgr = ctx.get("route_manager")
    state_machine = ctx.get("state_machine")

    # 1. Trigger synthetic ambulance visual on CAM-J1-NORTH
    source = stream_mgr.get_source("CAM-J1-NORTH") if stream_mgr else None
    if source:
        source.trigger_demo_ambulance()

    # 2. Ingest sample route
    sample_points = [
        {"lat": 12.9660, "lng": 77.5880},
        {"lat": 12.9716, "lng": 77.5946}, # J-101
        {"lat": 12.9758, "lng": 77.6012}, # J-102
        {"lat": 12.9812, "lng": 77.6085}, # J-103
    ]
    if route_mgr:
        route_mgr.ingest_route(
            ambulance_id="AMB-DEMO-99",
            route_points=sample_points,
            junctions_on_route=["J-101", "J-102", "J-103"],
            progress_percent=15.0,
            emergency_severity="CRITICAL"
        )

    # 3. Trigger immediate corridor pre-emption on J-101
    if state_machine:
        state_machine.trigger_preemption(
            junction_id="J-101",
            ambulance_id="AMB-DEMO-99",
            reason="DEMO_MANUAL_TRIGGER",
            severity="CRITICAL",
            eta_seconds=12.0,
            distance_meters=180.0
        )

    return {
        "status": "DEMO_DISPATCHED",
        "ambulance_id": "AMB-DEMO-99",
        "message": "Demo ambulance dispatched on CAM-J1-NORTH and corridor J-101 switched to GREEN."
    }


@router.post("/demo/trigger_camera/{camera_id}")
def trigger_camera_ambulance(camera_id: str) -> Dict[str, Any]:
    """
    Forces an ambulance appearance in the specified synthetic camera feed.
    """
    ctx = get_context()
    stream_mgr = ctx.get("stream_manager")
    source = stream_mgr.get_source(camera_id) if stream_mgr else None
    if not source:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

    source.trigger_demo_ambulance()
    return {"status": "SUCCESS", "camera_id": camera_id, "message": "Ambulance dispatched on camera."}


@router.post("/signals/manual_override")
def manual_signal_override(junction_id: str, state: str, reason: str = "MANUAL_OPERATOR_OVERRIDE") -> Dict[str, Any]:
    """
    Allows traffic engineers to force signal state (RED / GREEN / HOLD) for testing.
    """
    ctx = get_context()
    state_machine = ctx.get("state_machine")
    if not state_machine:
        raise HTTPException(status_code=500, detail="State machine not initialized")

    if state.upper() == "GREEN":
        state_machine.trigger_preemption(junction_id, "OPERATOR_OVERRIDE", reason=reason)
    elif state.upper() == "HOLD":
        state_machine.trigger_hold(junction_id, "OPERATOR_OVERRIDE")
    else:
        state_machine.trigger_clearance(junction_id, "OPERATOR_OVERRIDE", reason=reason)

    return {"status": "OVERRIDDEN", "junction_id": junction_id, "state": state.upper()}


@router.get("/api/config")
def get_client_config() -> Dict[str, Any]:
    """
    Returns public configuration for the Google Maps JavaScript frontend dashboard.
    """
    ctx = get_context()
    settings: AppSettings = ctx.get("settings", get_settings())

    return {
        "app_name": settings.name,
        "version": settings.version,
        "google_maps_api_key": settings.google_maps_api_key,
        "signal_controller_type": settings.signal_controller_type,
        "junctions": [j.model_dump() for j in settings.junctions],
        "cameras": [c.model_dump() for c in settings.cameras]
    }


# ==============================================================================
# WEBSOCKET ENDPOINT
# ==============================================================================

@router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket event stream for SirenSync UI and external modules.
    Streams AMBULANCE_DETECTED, SIGNAL_CHANGED, ROUTE_UPDATED, and CONFLICT_DETECTED.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open; clients can also send ping/heartbeat
            data = await websocket.receive_text()
            if data.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"[WEBSOCKET] Connection closed: {e}")
        ws_manager.disconnect(websocket)
