# SirenSync Three-Module Integration Work Report

## Integration scope

The supplied integrated repository and Nidhi ambulance-module ZIP were reviewed together. The integrated repository remains the source of truth; the ambulance module was retained within that application rather than run as a separate backend.

## Shared data architecture verified

- `backend/database/session.py` is the operational SQLAlchemy session used by hospital, emergency, reservation, ambulance and tracking APIs.
- Ambulance records reference the existing `emergencies.id` and `hospitals.id` tables.
- Ambulance dispatch updates the existing `hospital_queue_items` row by `emergency_id`.
- Patient authentication continues to use its existing separate `sirensync.db` database/session. This preserves the existing patient accounts and sessions; it is not an ambulance database.
- No new queue table, ambulance database, emergency table, or ambulance-specific SQLAlchemy Base was introduced.

## Data files supplied and retained

The package includes copies of the three user-supplied files under `database/`:

- `database/sirensync_hospital.db`
- `database/sirensync.db`
- `database/backups/sirensync_hospital_backup_pre_phase1_20261122.db`

The operational database copy passed `PRAGMA integrity_check` and retained the supplied counts: 9 hospitals, 42 emergencies, 282 beds, 37 bed reservations, 37 hospital queue items, 9 reassignment audit records and 10 existing ambulance rows.

The authentication database copy passed `PRAGMA integrity_check` and retained 47 patient rows and 92 session rows.

The backup remains a backup and is not selected as the active operational database. Existing Bengaluru demo ambulance rows were preserved; no additional ambulance seed records were inserted during this work.

## Integration wiring

- Ambulance and tracking routers are registered in the unified FastAPI application.
- The driver console is served at `/driver/`.
- The hospital dashboard is served at `/dashboard/`.
- Patient emergency status polls the tracking snapshot endpoint using the same emergency ID.
- Successful bed reservation triggers ambulance dispatch after the reservation transaction commits.
- No-ambulance behavior retains the reservation and writes the pending note to the existing queue item.
- Hospital queue API responses now include optional ambulance ID, vehicle number, driver name, status and simulated-telemetry indicator for the same emergency ID.
- Driver simulator waypoints now use the Dehradun demonstration corridor.
- The driver UI no longer offers a manual AVAILABLE-to-ASSIGNED action that the backend correctly rejects; dispatch remains hospital-coordinated.
- Database defaults resolve the existing sibling `database/` folder first, then the repository-local `database/` folder. Explicit environment-variable overrides remain supported.
- `backend/run.sh` now supports `.venv`, `venv`, or the active Python environment rather than assuming `backend/venv`.

## Verification performed

- Python compilation: passed for backend, seed and test modules.
- Driver and hospital JavaScript syntax checks: passed with `node --check`.
- Hospital/ambulance backend test suite: 65 passed.
- End-to-end reservation/dispatch/queue test now verifies ambulance details appear in the hospital queue.
- Concurrent duplicate dispatch test passed after rechecking an assignment won by a concurrent request.
- Unified FastAPI smoke checks against the supplied database copies: `/api/v1/ambulances` returned 10 records; `/api/v1/hospitals` returned 9 hospitals; `/driver/` and `/dashboard/` returned HTTP 200.
- Operational and authentication database copies passed SQLite integrity checks after restoration to the supplied data state.

## Verification limitations and remaining work

- Patient-authentication tests could not be validly executed in this environment because the `bcrypt` package was unavailable and package installation was blocked by network access. A temporary import shim was used only to load the application for non-auth tests; authentication test results are therefore not claimed.
- Patient and hospital Vite production builds could not be run because frontend dependencies were not installed and the npm package registry was unreachable. Existing source and lock files are included. Run `npm install` and `npm run build` locally for the patient frontend.
- The driver console is a prototype fleet-selection interface and does not yet implement authenticated driver accounts. Do not expose it publicly without adding driver authentication/authorization.
- GPS/route telemetry and traffic are simulated/mock unless a real provider is configured. No physical traffic-signal control or live Google Maps traffic integration is claimed.
- The existing reassignment workflow still requires a dedicated end-to-end test with an actually assigned ambulance and an alternate hospital bed. The current integration updates the ambulance destination and existing queue item in the reassignment transaction, but the workflow's alternate-bed reservation semantics should be reviewed before describing reassignment as production-safe.

## Local startup

Install backend dependencies and start the unified API:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
PYTHONPATH="$PWD/backend:$PWD" .venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

- Hospital: `http://localhost:8000/dashboard/`
- Driver: `http://localhost:8000/driver/`
- API docs: `http://localhost:8000/docs`

Run the patient portal separately:

```bash
cd frontend/patient
npm install
npm run dev -- --host 0.0.0.0
```

Open `http://localhost:5173`.

---

# Phase 2.2: Patient Live Tracking, Automatic Driver GPS, Traffic Routing & Dispatch Recovery

Date: 2026-11-22

## User-observed issues addressed

1. Patient Emergency Status did not reliably refresh after driver telemetry changed.
2. Driver had to manually enter route progress and coordinate waypoints.
3. A second emergency remained in `AMBULANCE_PENDING` even though the fleet showed available vehicles.
4. A pending dispatch needed a bounded escalation path without assigning an incompatible ambulance.

## Root causes found

- `EmergencyStatus.jsx` built a fallback emergency ID from `requestId`, but its original polling effects only ran when `activeEmergency.emergencyId` existed. This could leave a requestId-only patient session without tracking refresh.
- `Emergency.required_capabilities` contains hospital/facility capability codes as well as some explicit ambulance equipment requirements. The ambulance filter incorrectly treated `CARDIAC_CATH_LAB`, `STROKE_UNIT`, `TRAUMA_LEVEL_1`, and `OXYGEN_HDU` as equipment carried by an ambulance. That could exclude every available ambulance even when a compatible MICU/ALS unit existed.
- The driver screen only offered a simulated coordinate form and a manual route progress slider. It did not automatically use browser device geolocation.

## Implementation changes

### Patient status and hospital queue synchronization

- Patient tracking now uses the canonical emergency ID from `emergencyId`, `requestId`, or `emergency_id` consistently.
- Patient status opens an emergency-scoped WebSocket subscription and retains a 2.5-second REST snapshot polling fallback.
- Location, status and GPS-derived progress events update the patient tracking state without a page refresh.
- The patient status page displays the ambulance, driver, current coordinates, route progress, progress bar and last telemetry time.
- The schematic patient map now receives the live ambulance coordinates and selected hospital coordinates where available. Illustrative traffic graphics are labelled as illustrative, not live signal control.
- The lifecycle timeline is now data-driven from the actual ambulance status. The manual demo advance/reset controls and fabricated timestamps were removed.
- Patient view requests the current traffic-aware route every 60 seconds when an ambulance is assigned and shows the live ETA/distance only when the route provider returns traffic-aware data.

### Automatic driver GPS and route progress

- Driver dashboard now polls the fleet every five seconds. If a vehicle becomes assigned while the driver console is already open, it automatically selects the assigned vehicle.
- After assignment, the driver console starts `navigator.geolocation.watchPosition` and submits real device coordinates with `isSimulated=false` after the browser grants permission.
- Telemetry is throttled to avoid unnecessary requests and ignores tiny stationary GPS changes.
- Manual route-progress slider and coordinate waypoint controls were replaced with an automatic GPS panel.
- When a Google Routes polyline is available, route progress is calculated against its decoded road geometry. Without a traffic API key, the driver panel clearly identifies progress as a GPS distance estimate rather than claiming road-route or live-traffic accuracy.
- Location and GPS-derived progress are saved in one backend operation and synchronize the existing `HospitalQueueItem.route_progress`.
- First real GPS telemetry advances an assigned vehicle into `EN_ROUTE_PICKUP`; the existing hospital queue transitions to `EN_ROUTE` once progress is positive.
- The driver map draws Google route geometry when available and otherwise uses a clearly non-traffic-aware direct line.

### Live traffic integration

- Added a server-side Google Routes API provider using `TRAFFIC_AWARE_OPTIMAL` driving routes.
- Added `GET /api/v1/ambulances/{ambulance_id}/route` returning route geometry, road distance, traffic-aware duration and traffic advisory summary.
- The Google API key remains server-side and is never returned to the browser.
- Hospital ranking uses Google traffic-aware travel-time ratios when `GOOGLE_MAPS_API_KEY` is configured. Without a key it retains the existing deterministic MockTrafficProvider. If the configured Google provider has a transient ranking lookup failure, it uses a neutral traffic factor with an explicit unavailable explanation rather than silently pretending mock data is live.
- Live Google traffic cannot be verified in this environment because no Google API key was supplied. A billing-enabled Google Cloud project with Routes API enabled is required.

### Dispatch reliability and pending recovery

- Hospital-only capabilities (`CARDIAC_CATH_LAB`, `STROKE_UNIT`, `TRAUMA_LEVEL_1`, `OXYGEN_HDU`, and other non-equipment facility codes) no longer incorrectly disqualify ambulances.
- Explicit ambulance equipment requirements such as `VENTILATOR` and `ICU_VENTILATOR` remain hard eligibility filters.
- Added persistent retry metadata to the existing `hospital_queue_items` table: `dispatch_pending_since`, `dispatch_attempt_count`, and `dispatch_escalated_at`.
- Added idempotent migrations for those fields. No new queue table or database was created.
- Backend retries pending reserved emergencies every 10 seconds using the same operational database, same emergency ID and same existing queue item.
- A successful retry clears pending metadata and updates that same queue item to `DISPATCHED`.
- After two minutes without an eligible ambulance, the existing queue notes indicate hospital-desk escalation while automatic retries continue. The system does not assign a clinically incompatible ambulance just to satisfy a timer.
- Existing bed reservations remain protected while dispatch is pending.

## Files changed

- `backend/models/queue.py`
- `backend/database/init_db.py`
- `backend/services/ambulance_service.py`
- `backend/services/traffic_provider.py`
- `backend/routers/ambulances.py`
- `backend/routers/reservations.py`
- `backend/main.py`
- `backend/.env.example`
- `.env.example`
- `frontend/patient/pages/EmergencyStatus.jsx`
- `frontend/patient/components/Timeline.jsx`
- `frontend/patient/components/MockMap.jsx`
- `frontend/patient/services/emergencyService.js`
- `frontend/driver/src/app.js`
- `frontend/driver/src/api.js`
- `frontend/driver/src/components/LocationSimulator.js`
- `frontend/driver/src/components/MapView.js`
- `frontend/driver/index.html`
- `tests_hospital/test_ambulance_dispatch.py`
- `tests_hospital/test_ambulance_tracking.py`
- `README.md`

## Database preservation

The packaged `database/sirensync_hospital.db` remains the operational database for hospitals, emergencies, beds, reservations, queue items and ambulances. The packaged `database/sirensync.db` remains the patient authentication/session database. The pre-Phase-1 backup remains under `database/backups/`.

The idempotent migration was run against the packaged operational database. SQLite integrity check returned `ok`. Existing row counts were preserved: 9 hospitals, 42 emergencies, 282 beds, 37 reservations, 37 hospital queue items, 9 reassignment audit logs and 10 ambulances. Patient authentication database integrity check also returned `ok`; patient/session records were preserved.

## Verification performed

- Python compilation passed for changed backend modules.
- Node syntax checks passed for the driver JavaScript modules.
- 26 targeted backend tests passed: ambulance dispatch, capability eligibility, concurrent dispatch, pending retry recovery, tracking, GPS-to-queue synchronization and reassignment policy.
- Tests were run with a temporary test-only bcrypt import shim because bcrypt is not installed in this execution environment. Patient authentication tests were not counted as passing and must be run on the user's Mac after installing `backend/requirements.txt`.
- Patient frontend production build could not be run in this environment because Vite/node_modules are not installed and network package installation is unavailable.
- Google Routes API live calls were not executed because no API key was supplied.
- Physical browser GPS was not exercised because this environment does not have a driver's mobile device or browser location permission.

## Required local activation for real GPS and live traffic

1. Install the backend dependencies from `backend/requirements.txt`.
2. For a real driver location, open `/driver/` on the driver's phone using HTTPS (or use `localhost` for a local browser test), grant browser location permission, and keep the driver page active.
3. In the backend terminal, set `export GOOGLE_MAPS_API_KEY="YOUR_SERVER_SIDE_KEY"` before starting Uvicorn. Enable Routes API and billing in Google Cloud and restrict the key to Routes API.
4. Restart Uvicorn after setting the key. The driver route panel and patient ETA panel will then use Google traffic-aware routes. Without the key, GPS still transmits but progress is labelled as an estimate and live traffic is not claimed.
5. Run `npm install && npm run build` in `frontend/patient` on the Mac to verify the patient production build.

## Remaining verification / product limitations

- Live Google traffic depends on the user's Google Cloud API key, billing and API enablement.
- Real GPS depends on a device with location services and browser permission; a Mac desktop location fix is not proof of an ambulance phone GPS deployment.
- Driver identity authentication is still a demo fleet-selection workflow, not production driver account authentication.
- Driver arrival/pickup lifecycle state transitions remain explicit driver workflow actions; route percentage and coordinates no longer require manual entry.
- Patient and hospital frontends must be rebuilt and exercised locally on the user's Mac before calling the package production-ready.
