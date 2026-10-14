# Registered-Plate Green Corridor

This is Ishita's isolated AI traffic module. It is a separate service and dashboard so the supplied patient, hospital, and ambulance code stays unchanged.

The dashboard uses an interactive OpenStreetMap street layer. It draws the route geometry supplied by ambulance dispatch/tracking and moves the ambulance marker along that geometry using route progress/GPS. The map does not calculate road directions itself: dispatch must send its road-following polyline (`route_points`). If only origin and destination are supplied, the fallback is a straight line and will not follow streets. Map tiles require an internet connection and show OpenStreetMap attribution. The visible map area is requested from the tile provider; the ambulance plate and full route polyline are not sent to that provider.

## How the module works

1. The selected hospital coordinates the ambulance response. Nidhi's backend allocates a route and knows the ambulance database ID plus its `vehicle_number`.
2. After allocation, the dispatch/route producer posts the active ambulance ID, registered vehicle number, route points, and junction list to this service's `POST /route` endpoint.
3. A configured road camera reads number plates. Live camera feeds use OpenCV plate localization and Tesseract OCR. Only an exact normalized number in `registry.json` that belongs to an active route is verified.
4. A verified plate at a configured route junction, or a verified ambulance GPS update inside the configured approach radius, requests corridor priority. Unregistered plates and plates with no active route do not change signals.
5. The virtual signals run `CLEARING_TO_CORRIDOR` (conflicting green turns amber) → `ALL_RED_TO_CORRIDOR` → `EMERGENCY_GREEN`. After the tracked ambulance passes, they run `CLEARING_AFTER_PASS` → `ALL_RED_TO_NORMAL` → the configured normal cycle. A maximum-green timer prevents a simulated phase from staying green forever.

**This module never sends commands to physical traffic lights.** The built-in sample camera draws a sample plate and marks its own generated plate as deterministic simulated sensor metadata. It does not perform real OCR. Live camera mode uses OpenCV and Tesseract and requires a configured camera feed, the Python package, and the native Tesseract executable. The dashboard reports clearly whether it is in synthetic or live mode.

## Run the backend and frontend

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r ai_traffic/registered_corridor/requirements.txt
python -m uvicorn ai_traffic.registered_corridor.api:app --host 127.0.0.1 --port 8010 --reload
```

Open [http://127.0.0.1:8010](http://127.0.0.1:8010). The backend serves the frontend from this module's `frontend/index.html`; it does not replace the team's patient or driver frontends. The sample dispatch button allocates a sample route, starts the camera feed and simulates GPS progress.

## Connect after Nidhi's route allocation

The route API uses the team's ambulance ID and registered `vehicle_number`. It accepts the shared AI-traffic `route_points` / `junctions` shape and also the ambulance response's camelCase names:

```http
POST http://127.0.0.1:8010/route
Content-Type: application/json
```

```json
{
  "ambulanceId": "AMB-001",
  "vehicleNumber": "KA03AB1234",
  "emergencySeverity": "CRITICAL",
  "junctions": ["J-101", "J-102"],
  "routePoints": [
    {"lat": 12.9680, "lng": 77.5910},
    {"lat": 12.9716, "lng": 77.5946},
    {"lat": 12.9758, "lng": 77.6012}
  ]
}
```

The same fields can be snake_case (`ambulance_id`, `vehicle_number`, `route_points`). If Nidhi's route provider has only origin/destination, send `origin` and `destination` as `"latitude,longitude"`; the module makes a straight sample route between them. For junction-accurate corridor timing, send the route polyline and ordered junction IDs.

Forward Nidhi's route progress to `POST http://127.0.0.1:8010/route/progress` alongside the existing team telemetry call:

```json
{
  "ambulanceId": "AMB-001",
  "routeProgress": 28.0,
  "latitude": 12.9709,
  "longitude": 77.5940
}
```

Coordinates are optional; progress is sufficient for the sample route interpolation. The existing tracking backend calls remain the source of truth for ambulance and patient tracking.

## Configure number plates and live cameras

- `registry.json` is the traffic module's local allow-list. Copy the ambulance ID and `vehicle_number` from Nidhi's fleet records; normalize differences in spaces/hyphens automatically. The incoming route is rejected unless both values match the allow-list.
- `config.json` stores junction coordinates, camera-to-junction associations, approach distance and signal timings. The map uses these coordinates for junction markers.
- The dispatch route's `route_points` must be its ordered, road-following polyline for the blue line and moving ambulance to match the actual streets. Do not send only two endpoints if the route was already computed elsewhere.
- For a webcam, set a camera's `source` to `camera` and `url` to `"0"`. For a permitted RTSP feed, set `url` to its RTSP URL. Do not place camera passwords in a committed config file.
- Live OCR needs Tesseract installed on the computer. If the executable is not on `PATH`, set `TESSERACT_CMD` to its full path before starting the backend.

## API and live frontend events

- `GET /api/health`, `/api/registry`, `/api/routes`, `/api/signals`, `/api/events`
- `GET /video/{camera_id}` for an annotated MJPEG camera stream
- `POST /route` and `/route/progress` for the upstream route/telemetry contract
- `POST /api/demo/start` for the isolated sample demo
- `ws://127.0.0.1:8010/ws/events` for `ROUTE_ALLOCATED`, `PLATE_VERIFIED`, `PLATE_REJECTED`, `CORRIDOR_REQUESTED`, `SIGNAL_CHANGED`, `JUNCTION_PASSED`, and `ROUTE_UPDATED`

The local plate allow-list is for prototype integration. In a deployment, the fleet service should provide an authenticated registry lookup, and physical signal control would require a separate authorized, fail-safe municipal integration.
