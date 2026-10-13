"""
Main FastAPI server for SirenSync AI-Traffic module.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, Dict, List
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import yaml

# Ensure both project root and ai_traffic folder are on Python path
_current_dir = Path(__file__).resolve().parent
_project_root = _current_dir.parent
for _p in [str(_project_root), str(_current_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from ai_traffic.camera import get_mjpeg_stream, get_camera_frame, set_annotated_frame, start_cameras
    from ai_traffic.detector import detect_ambulance, init_detector
    from ai_traffic.route import get_active_route, set_active_route, update_ambulance_location
    from ai_traffic.signals import check_signal_timers, get_all_junction_states, init_signals, trigger_green
except ImportError:
    from camera import get_mjpeg_stream, get_camera_frame, set_annotated_frame, start_cameras
    from detector import detect_ambulance, init_detector
    from route import get_active_route, set_active_route, update_ambulance_location
    from signals import check_signal_timers, get_all_junction_states, init_signals, trigger_green

# Load environment variables
load_dotenv()

# In-memory store of the last 100 events
events_history: List[dict] = []

# Active WebSocket connections
_ws_connections: List[WebSocket] = []
_loop: Any = None
_running = True

# Load configuration file
_config_path = Path(__file__).parent / "config.yaml"
with open(_config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


# Records an event in memory (up to 100 items) and broadcasts it to WebSocket clients
def emit_event(event_type: str, data: dict):
    now_ts = datetime.now(timezone.utc).isoformat()
    record = {"event_type": event_type, "timestamp": now_ts, **data}

    events_history.append(record)
    if len(events_history) > 100:
        events_history.pop(0)

    # Broadcast via WebSocket
    disconnected = []
    for ws in _ws_connections:
        try:
            if _loop and _loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send_json(record), _loop)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in _ws_connections:
            _ws_connections.remove(ws)


# Background worker that runs computer vision on camera streams and checks signal timers
def vision_worker():
    print("[WORKER] Vision and signal watchdog worker running...")
    prev_states = {}

    while _running:
        # 1. Process camera streams with YOLO
        for cam in config.get("cameras", []):
            cam_id = cam.get("camera_id")
            j_id = cam.get("junction_id")

            raw = get_camera_frame(cam_id)
            confirmed, score, annotated = detect_ambulance(raw, cam_id)
            set_annotated_frame(cam_id, annotated)

            if confirmed:
                emit_event("AMBULANCE_DETECTED", {
                    "camera_id": cam_id,
                    "junction_id": j_id,
                    "confidence": score,
                    "method": "anpr",          # primary method; beacon/yolo also possible
                    "plate": None,             # set by plates.py when a match is found
                    "matched_plate": None,     # registry plate string
                    "ambulance_id": None       # registry ambulance_id
                })
                trigger_green(j_id, f"AMB-{cam_id}", reason="CAMERA_CONFIRMED")

        # 2. Check signal timers (amber intervals and safety timeouts)
        green_cfg = config.get("green_corridor", {})
        check_signal_timers(
            hold_after_pass_s=green_cfg.get("hold_after_pass_s", 5.0),
            amber_duration_s=green_cfg.get("amber_duration_s", 3.0),
            max_green_s=green_cfg.get("max_green_s", 60.0)
        )

        # 3. Detect signal state changes and emit event
        for j in get_all_junction_states():
            j_id = j["junction_id"]
            new_st = j["state"]
            if prev_states.get(j_id) != new_st:
                prev_states[j_id] = new_st
                emit_event("SIGNAL_CHANGED", {
                    "junction_id": j_id,
                    "state": new_st,
                    "reason": j.get("reason", "TIMER")
                })

        time.sleep(0.05)


# Application startup and shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop, _running
    _loop = asyncio.get_running_loop()

    # Initialize modules
    init_signals(config.get("junctions", []), controller_type=os.getenv("SIGNAL_CONTROLLER_TYPE", "simulated"))
    init_detector(config.get("detection", {}).get("weights_path", "yolov10n_ambulance.pt"))
    start_cameras(config.get("cameras", []))

    # Start vision worker thread
    _running = True
    t = threading.Thread(target=vision_worker, daemon=True)
    t.start()

    yield
    _running = False


# Create FastAPI application
app = FastAPI(title="SirenSync Green Corridor", lifespan=lifespan)


# Returns module operational health
@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "app": config.get("app", {}).get("name", "SirenSync Green Corridor"),
        "controller": os.getenv("SIGNAL_CONTROLLER_TYPE", "simulated")
    }


# Returns all junctions and their current signal lights
@app.get("/junctions")
def get_junctions():
    return get_all_junction_states()


# Returns the last 100 in-memory events
@app.get("/events")
def get_events():
    return list(reversed(events_history))


# Accepts route JSON from upstream ambulance coordinator
@app.post("/route")
def post_route(route: dict):
    set_active_route(route)
    return {"status": "accepted", "ambulance_id": route.get("ambulance_id")}


# Streams live MJPEG video for the requested camera
@app.get("/video_feed/{cam_id}")
def video_feed(cam_id: str):
    return StreamingResponse(get_mjpeg_stream(cam_id), media_type="multipart/x-mixed-replace; boundary=frame")


# Dispatches a simulated ambulance approach for testing
@app.post("/demo/dispatch")
def demo_dispatch():
    trigger_green("J-1", "AMB-DEMO-01", reason="DEMO_BUTTON_CLICKED")
    return {"status": "dispatched", "junction_id": "J-1"}


# Returns public config parameters for the frontend dashboard
@app.get("/api/config")
def get_public_config():
    return {
        "google_maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY", ""),
        "junctions": config.get("junctions", [])
    }


# WebSocket stream broadcasting AMBULANCE_DETECTED and SIGNAL_CHANGED events
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    _ws_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)


# Serves the single-page web dashboard at the root URL
@app.get("/")
def get_dashboard():
    index_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(str(index_path))


# Direct Python entry point (run with: python main.py or python ai_traffic/main.py)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

