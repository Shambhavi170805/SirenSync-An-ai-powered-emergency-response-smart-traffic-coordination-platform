"""Standalone backend for Ishita's registered-number green-corridor module."""

import asyncio
import json
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse

from ai_traffic.registered_corridor.camera import CameraHub
from ai_traffic.registered_corridor.corridor_service import CorridorService
from ai_traffic.registered_corridor.models import RouteAllocation, RouteProgress
from ai_traffic.registered_corridor.plate_reader import PlateReader
from ai_traffic.registered_corridor.registry import VehicleRegistry


MODULE_DIR = Path(__file__).resolve().parent
config = json.loads((MODULE_DIR / "config.json").read_text(encoding="utf-8"))
registry = VehicleRegistry(MODULE_DIR / "registry.json")
service: CorridorService | None = None
cameras: CameraHub | None = None
event_loop: asyncio.AbstractEventLoop | None = None
websocket_clients: set[WebSocket] = set()
events: list[dict] = []
events_lock = threading.Lock()


async def _broadcast(event: dict) -> None:
    stale = []
    for client in tuple(websocket_clients):
        try:
            await client.send_json(event)
        except Exception:
            stale.append(client)
    for client in stale:
        websocket_clients.discard(client)


def emit_event(event_type: str, payload: dict) -> None:
    event = {"event_type": event_type, "timestamp": datetime.now(timezone.utc).isoformat(), **payload}
    with events_lock:
        events.append(event)
        del events[:-100]
    if event_loop and event_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast(event), event_loop)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global service, cameras, event_loop
    event_loop = asyncio.get_running_loop()
    service = CorridorService(config, registry, emit_event)
    service.signals.initialize(list(service.junctions))
    reader = PlateReader()
    cameras = CameraHub(config["cameras"], reader, service.confirm_plate)
    service.start()
    cameras.start()
    try:
        yield
    finally:
        cameras.stop()
        service.stop()
        event_loop = None


app = FastAPI(title="SirenSync Registered-Plate Green Corridor", lifespan=lifespan)


@app.get("/")
def dashboard():
    return FileResponse(MODULE_DIR / "frontend" / "index.html")


@app.get("/api/health")
def health():
    has_live_camera = any(item.get("source") != "synthetic" for item in config["cameras"])
    if not has_live_camera:
        plate_status = "Synthetic sample only (not real OCR)"
    elif cameras and cameras.plate_reader.ready:
        plate_status = "Live camera · Tesseract executable ready"
    else:
        plate_status = "Live camera · Tesseract unavailable"
    return {
        "status": "ok",
        "signal_controller": "simulated-only",
        "plate_reader": plate_status,
        "cameras": cameras.get_status() if cameras else {},
        "active_routes": len(service.list_routes()) if service else 0,
    }


@app.get("/api/registry")
def get_registry():
    return registry.list_public()


@app.get("/api/routes")
def get_routes():
    return service.list_routes() if service else []


@app.get("/api/signals")
def get_signals():
    return service.signals.snapshot() if service else []


@app.get("/api/junctions")
def get_junctions():
    return config["junctions"]


@app.get("/api/events")
def get_events():
    with events_lock:
        return list(reversed(events))


@app.post("/route")
@app.post("/api/routes/allocate")
def allocate_route(request: RouteAllocation):
    """Call this after the selected hospital's dispatch assigns the ambulance route."""
    if not service:
        raise HTTPException(503, "Traffic service is starting")
    try:
        payload = request.dict()
        payload["route_points"] = [point.dict() for point in request.route_points] if request.route_points else None
        return {"status": "ALLOCATED", "route": service.allocate_route(payload)}
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.post("/route/progress")
@app.post("/api/routes/progress")
def update_progress(request: RouteProgress):
    """Forward Nidhi's ambulance progress update; GPS coordinates are optional."""
    if not service:
        raise HTTPException(503, "Traffic service is starting")
    try:
        return {"status": "UPDATED", "route": service.update_progress(
            request.ambulance_id, request.progress_percent, request.current_lat, request.current_lng
        )}
    except KeyError as exc:
        raise HTTPException(404, str(exc))


@app.get("/video/{camera_id}")
def video_feed(camera_id: str):
    if not cameras or camera_id not in cameras.cameras:
        raise HTTPException(404, "Camera is not configured")
    return StreamingResponse(cameras.mjpeg(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/demo/start")
def start_demo():
    """Start an allocated demo route and its built-in sample camera vehicle."""
    if not service or not cameras:
        raise HTTPException(503, "Traffic service is starting")
    payload = config["demo_route"]
    route = service.allocate_route(payload)
    demo_camera = next((c for c in config["cameras"] if c["junction_id"] in payload["junctions"] and c["source"] == "synthetic"), None)
    if not demo_camera or not cameras.dispatch_demo(demo_camera["camera_id"], payload["vehicle_number"]):
        raise HTTPException(409, "No synthetic camera is configured for this route")
    threading.Thread(target=service.demo_progress, args=(payload["ambulance_id"],), daemon=True).start()
    return {"status": "DEMO_STARTED", "route": route, "camera_id": demo_camera["camera_id"]}


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_clients.discard(websocket)

