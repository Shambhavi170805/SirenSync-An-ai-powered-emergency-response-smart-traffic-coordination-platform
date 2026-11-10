# SirenSync Route-Specific Green Corridor

This is Ishita's traffic module. It is isolated under `ai_traffic/registered_corridor`; it does not edit the patient, hospital, or ambulance modules.

## Pilot area and flow

The first pilot covers the Bengaluru Urban area in the supplied hospital sample. It contains five hospitals, while the number and locations of monitored junctions are discovered separately for each selected trip. The module does not use a fixed three-junction list.

1. Shambhavi provides the patient's location, selected hospital ID, and (when available) the selected road route as ordered `routePoints`.
2. `POST /api/route/plan` uses the supplied route points when present, map-matches that path to the road network, and discovers its intersections. It calculates up to three local OSM route choices only when no upstream route points were supplied.
3. Dispatch selects a route and allocates an ambulance to it with `POST /route`. The module checks the registered ambulance and attaches the route to its emergency.
4. A configured camera reads the vehicle plate. An exact registered plate on the active route verifies the ambulance. Camera feeds with known coordinates are associated with the closest discovered route junction; a local test webcam without coordinates is associated with the route entry.
5. GPS from the tracking API advances the ambulance along the route. As it approaches each discovered junction, that junction's simulated signal clears cross traffic, gives the ambulance a green phase, and returns to its normal cycle after the ambulance passes.

OSRM uses OpenStreetMap road data to map-match a supplied route and identify its intersections; the local fallback requests a route when Shambhavi's path is unavailable. Neither provides live congestion predictions. See the [OSRM Match service documentation](https://project-osrm.org/docs/v26.4.0/http#match-service) and [Route service documentation](https://project-osrm.org/docs/v26.4.0/http#route-service).

**Signals are simulated. This module does not control physical traffic lights.** A laptop webcam is a local camera-pipeline input, not a junction CCTV feed. Use an authorized accessible camera feed for a field pilot. Number-plate OCR, camera placement, GPS, and signal timing need field validation before road deployment.

## Run locally

From the repository root in PowerShell:

```powershell
& C:\Users\ishit\.venv\Scripts\python.exe -m pip install -r ai_traffic/registered_corridor/requirements.txt
& C:\Users\ishit\.venv\Scripts\python.exe -m uvicorn ai_traffic.registered_corridor.api:app --host 127.0.0.1 --port 8010 --reload
```

Open [http://127.0.0.1:8010](http://127.0.0.1:8010). Enter the patient latitude/longitude from Shambhavi and choose the hospital selected for the emergency. If testing manually, open **Optional: use Shambhavi's selected route** and paste its ordered `[{"lat": ..., "lng": ...}]` route points. The map then displays that selected path with its detected intersections. Leave it blank for the local OSM fallback. Use **Run simulated camera/GPS demonstration** for the sample plate and virtual signal sequence, or allocate an active ambulance after dispatch.

Route planning needs an internet connection to the configured routing server. The default is the public OSRM demo endpoint for a small prototype. Set `SIRENSYNC_ROUTER_BASE_URL` to a compatible OSRM service if you run your own. For field or high-volume use, host and operate a routing service under the project team's control.

## Shambhavi and hospital handoff

The route planner accepts the patient-location shape used by Shambhavi and the chosen hospital ID:

```http
POST http://127.0.0.1:8010/api/route/plan
Content-Type: application/json
```

```json
{
  "emergencyId": "emg-9821a",
  "patientLocation": {"latitude": 12.9716, "longitude": 77.5946},
  "hospitalId": "hosp-manipal-hal",
  "routePoints": [
    {"lat": 12.9716, "lng": 77.5946},
    {"lat": 12.9742, "lng": 77.5991},
    {"lat": 12.9592, "lng": 77.6477}
  ]
}
```

`routePoints` is optional and must be an ordered road path inside the configured pilot area. It can be sent as `routePoints` or `route_points`; GeoJSON `routeGeometry.coordinates` is also accepted. When it is present, the module map-matches that path and does not choose a different origin-to-hospital route. The response labels the source as `SHAMBHAVI_SELECTED_ROUTE`. If omitted, it labels the locally calculated fallback as `LOCAL_OSM_FALLBACK`.

`GET /api/hospitals` returns the local five-hospital pilot directory. With Nidhi's API integration enabled, it reads the team's `/api/v1/hospitals` directory instead and limits the choices to the pilot area's configured bounds. The location passed to `/api/route/plan` must also fall inside those bounds.

The response contains `route_plan_id` and one or more `options`. Each option includes `route_points`, `junctions`, `distance_m`, and `duration_s`. The UI lets the operator choose an option before ambulance allocation.

## Nidhi ambulance tracking API handoff

The consumer is disabled by default, so the local sample can run without Nidhi's server. Enable it in the same PowerShell terminal before launching:

```powershell
$env:SIRENSYNC_TRACKING_API_ENABLED = "true"
$env:SIRENSYNC_TRACKING_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
$env:SIRENSYNC_TRACKING_WS_URL = "ws://127.0.0.1:8000/api/v1/tracking/ws"
& C:\Users\ishit\.venv\Scripts\python.exe -m uvicorn ai_traffic.registered_corridor.api:app --host 127.0.0.1 --port 8010 --reload
```

After a route plan is selected, dispatch allocates the ambulance through:

```http
POST http://127.0.0.1:8010/route
Content-Type: application/json
```

```json
{
  "ambulanceId": "amb-bengaluru-als-01",
  "vehicleNumber": "KA03AB1234",
  "emergencyId": "emg-9821a",
  "routePlanId": "<route_plan_id from the plan response>",
  "routeOption": 0
}
```

Before allocating, the traffic module checks Nidhi's `/api/v1/ambulances/by-emergency/{emergencyId}` response for the ambulance ID, registered plate, emergency assignment, and active status. It then subscribes to `/api/v1/tracking/ws` for that emergency and consumes its `SNAPSHOT`, `LOCATION_UPDATE`, `ROUTE_PROGRESS_UPDATE`, and `STATUS_CHANGE` events. It does not modify Nidhi's code or write location updates back to her API. `GET /api/health` shows adapter connection status.

The shared Nidhi API currently streams live GPS and route-progress events but does not include the selected road-route polyline. Shambhavi or the dispatch handoff therefore needs to send `routePoints` to `/api/route/plan`; Nidhi's location updates then move the ambulance on that exact planned path. Without those points, the module labels its OSRM route as a local fallback. A reroute to another hospital/path needs a new route plan and allocation. If a tracking update is far from the selected route, it is rejected and logged rather than activating the wrong junction.

## Camera setup

- `CAM-PILOT-LIVE` opens webcam `0` by default for local camera/OCR trials.
- `CAM-PILOT-DEMO` is a generated feed with simulated plate metadata; it is only for the end-to-end demo.
- To use an accessible camera stream, set `SIRENSYNC_CAMERA_URL` to its webcam index or RTSP URL. Set `SIRENSYNC_CAMERA_LAT` and `SIRENSYNC_CAMERA_LNG` to the camera's actual map location so the module associates it with the nearest discovered junction. Do not put camera credentials in committed files.
- Live OCR uses OpenCV plate-region localization and Tesseract. The same normalized plate must be read in two consecutive scans and exactly match the current registered plate. Install Tesseract OCR and set `TESSERACT_CMD` if it is not on `PATH`.
- More cameras can be added to the `cameras` array in `config.json`, with a unique ID, source URL, and actual `lat`/`lng` coordinates. Each feed can then map to the nearest junction on the selected route.

The `.env.example` file lists the optional settings. This service does not load `.env` files automatically.

## Pilot area settings

- `hospitals.json` contains the five local sample hospitals sourced from the supplied team seed data.
- `config.json` defines the Bengaluru pilot boundary, signal timing, local camera feed definitions, and map center. The boundary is a development scope, not a statement that every road in that area has a camera.
- Junction coordinates are generated per route from OSM routing results and registered only for that trip. To expand the pilot, update the area boundary and hospital/camera directory; junctions remain route-derived.

## Endpoints

- `GET /api/health`, `/api/hospitals`, `/api/registry`, `/api/routes`, `/api/junctions`, `/api/signals`, `/api/events`
- `POST /api/route/plan` plans a street route and finds its intersections
- `POST /route` allocates a selected route to a registered ambulance
- `POST /route/progress` accepts a direct GPS/progress update when the tracking API consumer is off
- `POST /api/demo/start` runs the selected plan with the local sample camera (disabled in API-connected mode)
- `GET /video/{camera_id}` serves the selected annotated camera feed
- `ws://127.0.0.1:8010/ws/events` streams plate, route, junction, and simulated signal events
