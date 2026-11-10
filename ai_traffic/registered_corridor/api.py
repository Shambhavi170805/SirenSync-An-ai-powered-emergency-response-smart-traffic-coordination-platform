"""Standalone backend for Ishita's registered-number green-corridor module."""

import asyncio
import json
import os
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse

from ai_traffic.registered_corridor.camera import CameraHub
from ai_traffic.registered_corridor.corridor_service import CorridorService
from ai_traffic.registered_corridor.models import DemoStartRequest, RouteAllocation, RoutePlanRequest, RouteProgress
from ai_traffic.registered_corridor.plate_reader import PlateReader
from ai_traffic.registered_corridor.registry import VehicleRegistry
from ai_traffic.registered_corridor.registry import normalize_plate
from ai_traffic.registered_corridor.upstream import TrackingConsumer
from ai_traffic.registered_corridor.routing import OSMRoutePlanner


MODULE_DIR = Path(__file__).resolve().parent
config = json.loads((MODULE_DIR / "config.json").read_text(encoding="utf-8"))
camera_configs = [dict(item) for item in config["cameras"]]
live_camera_url = os.getenv("SIRENSYNC_CAMERA_URL")
for camera in camera_configs:
    if camera["camera_id"] == "CAM-PILOT-LIVE":
        if live_camera_url is not None:
            camera["source"] = "camera"
            camera["url"] = live_camera_url
        if os.getenv("SIRENSYNC_CAMERA_LAT") and os.getenv("SIRENSYNC_CAMERA_LNG"):
            camera["lat"] = float(os.environ["SIRENSYNC_CAMERA_LAT"])
            camera["lng"] = float(os.environ["SIRENSYNC_CAMERA_LNG"])
registry = VehicleRegistry(MODULE_DIR / "registry.json")
hospital_data = json.loads((MODULE_DIR / "hospitals.json").read_text(encoding="utf-8"))
route_planner = OSMRoutePlanner()
route_plans: dict[str, dict] = {}
service: CorridorService | None = None
cameras: CameraHub | None = None
event_loop: asyncio.AbstractEventLoop | None = None
websocket_clients: set[WebSocket] = set()
events: list[dict] = []
events_lock = threading.Lock()
tracking_consumer: TrackingConsumer | None = None


def _tracking_api_enabled() -> bool:
    return os.getenv("SIRENSYNC_TRACKING_API_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _within_pilot_area(latitude: float, longitude: float) -> bool:
    bounds = config["pilot_bounds"]
    return (bounds["min_lat"] <= latitude <= bounds["max_lat"] and
            bounds["min_lng"] <= longitude <= bounds["max_lng"])


def _visible_route_junctions() -> list[str]:
    if not service:
        return []
    routes = service.list_routes()
    route = next((item for item in routes if item.get("status") == "ACTIVE"), None)
    if route is None and routes:
        route = routes[-1]
    return route.get("junctions", []) if route else []


def _consume_tracking_event(event_type: str, emergency_id: str, payload: dict) -> None:
    if not service:
        return
    ambulance_id = str(payload.get("ambulanceId") or payload.get("ambulance_id") or "")
    route = next((item for item in service.list_routes()
                  if item.get("emergency_id") == emergency_id and item.get("ambulance_id") == ambulance_id
                  and item.get("status") == "ACTIVE"), None)
    if not route:
        return

    if event_type == "STATUS_CHANGE":
        status = str(payload.get("status", "")).upper()
        if status == "ARRIVED":
            service.end_route(ambulance_id, "COMPLETED", "AMBULANCE_ARRIVED")
        elif status in {"AVAILABLE", "MAINTENANCE"}:
            service.end_route(ambulance_id, "CANCELLED", f"AMBULANCE_STATUS_{status}")
        if status in {"ARRIVED", "AVAILABLE", "MAINTENANCE"} and tracking_consumer:
            asyncio.create_task(tracking_consumer.unsubscribe(emergency_id))
        return

    if event_type == "SNAPSHOT":
        vehicle_number = normalize_plate(payload.get("vehicleNumber", ""))
        if vehicle_number and vehicle_number != route["vehicle_number"]:
            emit_event("TRACKING_EVENT_REJECTED", {
                "ambulance_id": ambulance_id, "emergency_id": emergency_id,
                "reason": "SNAPSHOT_PLATE_MISMATCH",
            })
            return
        location = payload.get("currentLocation") or {}
        latitude, longitude = location.get("latitude"), location.get("longitude")
        progress = payload.get("routeProgress", route.get("progress_percent", 0))
    elif event_type == "LOCATION_UPDATE":
        latitude, longitude = payload.get("latitude"), payload.get("longitude")
        progress = route.get("progress_percent", 0)
    else:  # ROUTE_PROGRESS_UPDATE
        latitude = longitude = None
        progress = payload.get("routeProgress", route.get("progress_percent", 0))

    try:
        service.update_progress(
            ambulance_id, progress, latitude, longitude,
            is_simulated=payload.get("isSimulated"), source=f"TRACKING_API_{event_type}",
        )
    except (ValueError, KeyError) as exc:
        emit_event("TRACKING_EVENT_REJECTED", {
            "ambulance_id": ambulance_id, "emergency_id": emergency_id,
            "reason": str(exc), "source_event": event_type,
        })


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
    global service, cameras, event_loop, tracking_consumer
    event_loop = asyncio.get_running_loop()
    service = CorridorService(config, registry, emit_event)
    service.signals.initialize(list(service.junctions))
    reader = PlateReader()
    cameras = CameraHub(
        camera_configs, reader, service.confirm_plate,
        max_association_distance_m=float(config.get("camera_match_distance_m", 180)),
    )
    service.start()
    cameras.start()
    tracking_consumer = TrackingConsumer(_consume_tracking_event)
    try:
        yield
    finally:
        if tracking_consumer:
            await tracking_consumer.stop()
            tracking_consumer = None
        cameras.stop()
        service.stop()
        event_loop = None


app = FastAPI(title="SirenSync Registered-Plate Green Corridor", lifespan=lifespan)


@app.get("/")
def dashboard():
    return FileResponse(MODULE_DIR / "frontend" / "index.html")


@app.get("/api/health")
def health():
    has_live_camera = any(item.get("source") != "synthetic" for item in camera_configs)
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
        "pilot_area": config.get("pilot_area", "Configured local pilot"),
        "pilot_bounds": config.get("pilot_bounds", {}),
        "cameras": cameras.get_status() if cameras else {},
        "active_routes": len(service.list_routes()) if service else 0,
        "ambulance_tracking_api": {
            "enabled": _tracking_api_enabled(),
            "connections": tracking_consumer.snapshot() if tracking_consumer else {},
        },
    }


@app.get("/api/registry")
def get_registry():
    return registry.list_public()


@app.get("/api/routes")
def get_routes():
    return service.list_routes() if service else []


@app.get("/api/signals")
def get_signals():
    if not service:
        return []
    visible = set(_visible_route_junctions())
    return [signal for signal in service.signals.snapshot() if signal["junction_id"] in visible]


@app.get("/api/junctions")
def get_junctions():
    if not service:
        return []
    return [service.junctions[junction_id] for junction_id in _visible_route_junctions()
            if junction_id in service.junctions]


@app.get("/api/hospitals")
async def get_hospitals():
    """Return the bounded local pilot hospitals or the connected team's directory."""
    if not _tracking_api_enabled():
        return hospital_data["hospitals"]
    api_base = os.getenv("SIRENSYNC_TRACKING_API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{api_base}/hospitals")
        response.raise_for_status()
        return [hospital for hospital in response.json()
                if _within_pilot_area(float(hospital["latitude"]), float(hospital["longitude"]))]
    except ImportError:
        raise HTTPException(503, "Install module requirements to read the hospital directory")
    except Exception as exc:
        raise HTTPException(503, f"Hospital directory unavailable: {exc}")


@app.post("/api/route/plan")
async def plan_route(request: RoutePlanRequest):
    """Plan a road route from Shambhavi's patient location to the selected hospital."""
    origin = {"lat": request.patient_location.latitude, "lng": request.patient_location.longitude}
    if not _within_pilot_area(origin["lat"], origin["lng"]):
        raise HTTPException(422, f"Patient location is outside the configured {config['pilot_area']} pilot area")

    if _tracking_api_enabled():
        api_base = os.getenv("SIRENSYNC_TRACKING_API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{api_base}/hospitals/{request.hospital_id}")
            response.raise_for_status()
            hospital = response.json()
        except ImportError:
            raise HTTPException(503, "Install module requirements to read hospital locations")
        except Exception as exc:
            raise HTTPException(503, f"Selected hospital is unavailable: {exc}")
    else:
        hospital = next((item for item in hospital_data["hospitals"] if item["id"] == request.hospital_id), None)
        if not hospital:
            raise HTTPException(404, "Selected hospital is not in the local pilot directory")

    if hospital.get("is_active") is False:
        raise HTTPException(409, "Selected hospital is not active")
    destination = {"latitude": float(hospital["latitude"]), "longitude": float(hospital["longitude"])}
    if not _within_pilot_area(destination["latitude"], destination["longitude"]):
        raise HTTPException(422, "Selected hospital is outside the configured Bengaluru Urban pilot area")
    try:
        if request.route_points:
            supplied_points = [point.dict() for point in request.route_points]
            outside_route = [point for point in supplied_points
                             if not _within_pilot_area(point["lat"], point["lng"])]
            if outside_route:
                raise HTTPException(
                    422,
                    f"Shambhavi's selected route leaves the configured {config['pilot_area']} pilot area",
                )
            options = [await route_planner.match_supplied_route(supplied_points)]
        else:
            options = await route_planner.plan(origin, destination)
    except ImportError:
        raise HTTPException(503, "Install module requirements to enable road routing")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Road route could not be planned: {exc}")

    route_plan_id = uuid.uuid4().hex
    plan = {
        "route_plan_id": route_plan_id,
        "emergency_id": request.emergency_id,
        "origin": {"latitude": origin["lat"], "longitude": origin["lng"]},
        "hospital": {
            "id": hospital["id"], "name": hospital["name"],
            "latitude": destination["latitude"], "longitude": destination["longitude"],
        },
        "route_source": "SHAMBHAVI_SELECTED_ROUTE" if request.route_points else "LOCAL_OSM_FALLBACK",
        "options": options,
    }
    route_plans[route_plan_id] = plan
    # Keep the in-process demo plans bounded during repeated route selections.
    while len(route_plans) > 50:
        route_plans.pop(next(iter(route_plans)))
    return plan


@app.get("/api/events")
def get_events():
    with events_lock:
        return list(reversed(events))


@app.post("/route")
@app.post("/api/routes/allocate")
async def allocate_route(request: RouteAllocation):
    """Call this after the selected hospital's dispatch assigns the ambulance route."""
    if not service:
        raise HTTPException(503, "Traffic service is starting")
    payload = request.dict()
    plan = route_plans.get(request.route_plan_id or "")
    if not plan:
        raise HTTPException(422, "Plan a route from patient location to the selected hospital before allocating it")
    if request.emergency_id and plan.get("emergency_id") and request.emergency_id != plan["emergency_id"]:
        raise HTTPException(409, "Emergency ID does not match the selected route plan")
    if not payload.get("emergency_id"):
        payload["emergency_id"] = plan.get("emergency_id")
    if request.route_option >= len(plan["options"]):
        raise HTTPException(422, "Selected route option is no longer available")
    selected = plan["options"][request.route_option]
    payload["route_points"] = selected["route_points"]
    payload["junctions"] = selected["junction_ids"]
    payload["hospital_id"] = plan["hospital"]["id"]
    payload["hospital_name"] = plan["hospital"]["name"]
    if _tracking_api_enabled() and not payload.get("emergency_id"):
        raise HTTPException(422, "emergencyId is required when tracking API integration is enabled")
    if _tracking_api_enabled():
        api_base = os.getenv("SIRENSYNC_TRACKING_API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{api_base}/ambulances/by-emergency/{payload['emergency_id']}")
            response.raise_for_status()
            ambulance = response.json()
        except ImportError:
            raise HTTPException(503, "Install ai_traffic/registered_corridor/requirements.txt to enable API integration")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(502, f"Ambulance API validation failed: HTTP {exc.response.status_code}")
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, f"Ambulance API is unavailable: {exc}")
        assigned_emergency = ambulance.get("assignedEmergencyId")
        if ambulance.get("id") != request.ambulance_id or normalize_plate(ambulance.get("vehicleNumber", "")) != normalize_plate(request.vehicle_number):
            raise HTTPException(409, "Route ambulance ID/plate does not match the ambulance API record")
        if assigned_emergency != payload["emergency_id"]:
            raise HTTPException(409, "Ambulance API record is not assigned to this emergency")
        active_statuses = {"ASSIGNED", "EN_ROUTE_PICKUP", "PATIENT_ONBOARD", "EN_ROUTE_HOSPITAL"}
        api_status = str(ambulance.get("status", "")).upper()
        if api_status not in active_statuses:
            raise HTTPException(409, f"Ambulance status '{api_status}' is not active for corridor allocation")
        registry.sync_from_ambulance_api(ambulance)
        payload["is_simulated"] = ambulance.get("isSimulated", True)
    try:
        service.register_junctions(selected["junctions"])
        if cameras:
            cameras.assign_route_junctions(selected["junctions"])
        previous_route = service.get_route(request.ambulance_id)
        route = service.allocate_route(payload)
        if _tracking_api_enabled() and payload.get("emergency_id") and tracking_consumer:
            if previous_route and previous_route.get("emergency_id") and previous_route["emergency_id"] != payload["emergency_id"]:
                await tracking_consumer.unsubscribe(previous_route["emergency_id"])
            await tracking_consumer.subscribe(payload["emergency_id"], request.ambulance_id)
        return {"status": "ALLOCATED", "route": route}
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
            request.ambulance_id, request.progress_percent, request.current_lat, request.current_lng,
            is_simulated=request.is_simulated,
        )}
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.get("/video/{camera_id}")
def video_feed(camera_id: str):
    if not cameras or camera_id not in cameras.cameras:
        raise HTTPException(404, "Camera is not configured")
    return StreamingResponse(cameras.mjpeg(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/demo/start")
def start_demo(request: DemoStartRequest):
    """Run the selected dynamic hospital route with the local sample ambulance/camera."""
    if not service or not cameras:
        raise HTTPException(503, "Traffic service is starting")
    if _tracking_api_enabled():
        raise HTTPException(409, "The simulated sample cannot be used with the live ambulance API")
    plan = route_plans.get(request.route_plan_id)
    if not plan or request.route_option >= len(plan["options"]):
        raise HTTPException(404, "Plan a valid location-to-hospital route first")
    selected = plan["options"][request.route_option]
    service.register_junctions(selected["junctions"])
    cameras.assign_route_junctions(selected["junctions"])
    payload = {
        "ambulance_id": "AMB-DEMO-01",
        "vehicle_number": "KA03AB1234",
        "emergency_id": plan.get("emergency_id") or "emg-local-demo",
        "is_simulated": True,
        "route_points": selected["route_points"],
        "junctions": selected["junction_ids"],
        "hospital_id": plan["hospital"]["id"],
        "hospital_name": plan["hospital"]["name"],
        "emergency_severity": "CRITICAL",
    }
    route = service.allocate_route(payload)
    demo_camera = next((c for c in camera_configs if c["source"] == "synthetic"), None)
    if not demo_camera or not cameras.dispatch_demo(demo_camera["camera_id"], payload["vehicle_number"]):
        raise HTTPException(409, "No synthetic camera is configured for this route")
    threading.Thread(target=service.demo_progress, args=(payload["ambulance_id"],), daemon=True).start()
    return {
        "status": "DEMO_STARTED", "route": route,
        "camera_id": demo_camera["camera_id"], "hospital": plan["hospital"],
        "route_option": request.route_option,
    }


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_clients.discard(websocket)
