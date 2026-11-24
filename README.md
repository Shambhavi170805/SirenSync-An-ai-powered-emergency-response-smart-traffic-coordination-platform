# SirenSync Unified Emergency Response Platform

SirenSync connects the patient portal, hospital operations dashboard, and ambulance/driver console through one FastAPI backend and one shared operational database.

## Integrated application

- **Patient portal** (`frontend/patient/`): patient registration/login, emergency intake, capability-aware hospital ranking, hospital selection, bed reservation, and ambulance tracking.
- **Hospital dashboard** (`frontend/hospital/`): hospital directory, bed inventory, reservations, the existing emergency priority queue, reassignment evaluation, and assigned ambulance/driver details.
- **Driver console** (`frontend/driver/`): ambulance fleet, assignment view, lifecycle actions, simulated location/progress telemetry, and reroute notifications.
- **Backend** (`backend/`): one FastAPI application, shared SQLAlchemy Base and operational session for emergencies, hospitals, beds, reservations, queue items, and ambulances.

## Database layout and preservation

The application intentionally retains the two existing SQLite databases supplied with this project:

1. `database/sirensync_hospital.db` is the **shared operational database** for hospitals, emergencies, beds, reservations, `hospital_queue_items`, reassignment audit records, and ambulances. Patient emergency records and ambulance assignments are joined by the same `emergency_id`.
2. `database/sirensync.db` stores patient authentication records and sessions. It remains separate to preserve the existing patient-authentication implementation.
3. `database/backups/` contains the supplied pre-Phase-1 operational backup. It is a backup only and is not used by the application.

For compatibility with the existing Mac folder layout, database resolution first checks a sibling `database/` folder next to the repository. If that folder does not exist, it uses this repository's `database/` folder. Environment variables can override either path:

- `HOSPITAL_DATABASE_URL`
- `DATABASE_URL`

Do not point the two URLs to the same SQLite file. Do not replace the operational database with the pre-Phase-1 backup.

## Emergency lifecycle

1. Patient creates an emergency. The API persists `requiredCapabilities` on the emergency record.
2. Patient requests hospital ranking and selects a receiving hospital.
3. The existing bed reservation service atomically reserves a suitable bed and updates the existing `HospitalQueueItem`.
4. Ambulance dispatch runs after the bed reservation commits. It selects an available ambulance that satisfies required equipment constraints.
5. If no eligible ambulance is available, the bed reservation remains intact and the same queue item records that ambulance dispatch is pending.
6. Driver telemetry updates the ambulance record and the same queue item's route progress/status.
7. Patient tracking and hospital queue views read ambulance data using the same emergency ID.
8. Approved reroute events are applied within the existing reassignment transaction and broadcast after commit.

There is no separate ambulance queue or duplicate emergency table.

## Local setup (macOS)

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Start the unified backend:

```bash
PYTHONPATH="$PWD/backend:$PWD" .venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or use `backend/run.sh` after installing dependencies.

Open these backend-served interfaces:

- Hospital operations: http://localhost:8000/dashboard/
- Ambulance driver console: http://localhost:8000/driver/
- API documentation: http://localhost:8000/docs

Start the patient React/Vite portal in a second terminal:

```bash
cd frontend/patient
npm install
npm run dev -- --host 0.0.0.0
```

Open http://localhost:5173. The Vite development server proxies `/api` requests to the unified backend on port 8000.

The patient frontend can be built with `npm run build` from `frontend/patient`. The hospital dashboard and driver console are served as static vanilla-JavaScript applications by FastAPI and do not require a separate build step.

## Prototype and integration limitations

- Ambulance GPS/location and route progress are explicitly marked as simulated in the driver console unless a real telemetry source is configured.
- Traffic calculations use the configured provider (the default is deterministic mock traffic). This project does not claim real Google Maps live traffic ingestion or physical traffic-signal control.
- The driver console is a demonstration interface, not a production driver-authentication system. Do not expose it publicly without adding authenticated driver authorization.
- The 40% route-progress reassignment threshold is a configurable prototype rule, not a clinically validated policy.
- Cloudflare Turnstile and other external integrations require appropriate environment configuration for production use.

## Safety before using an existing local database

Keep a separate backup before running the application against any local operational database. Startup applies idempotent schema migrations. The application does not automatically seed new fleet records during normal startup.

## Live ambulance GPS and traffic-aware routing

The driver dashboard uses the driver's device browser GPS (`navigator.geolocation.watchPosition`) and sends real coordinates only after the driver grants location permission. Open `/driver/` on the driver's phone over HTTPS (or `localhost` during local testing). Do not use a simulated desktop waypoint and describe it as live GPS.

Traffic-aware road geometry and traffic duration are provided by Google Routes API when configured. Create a server-side API key in a billing-enabled Google Cloud project, enable Routes API, restrict the key to the Routes API, and set `GOOGLE_MAPS_API_KEY` in the backend process environment before starting Uvicorn. Example:

```bash
export GOOGLE_MAPS_API_KEY="YOUR_SERVER_SIDE_KEY"
```

The key is read only by the backend and is never sent to the browser. Without this key, device GPS still works, but route progress falls back to a clearly labelled GPS distance estimate and the map does not claim live traffic.

Ambulance dispatch retries every 10 seconds for reserved emergencies still in the existing `hospital_queue_items` coordination state. After two minutes without an eligible vehicle, the existing queue item is marked for hospital-desk escalation while retries continue. Hospital facility capabilities (such as a cardiac cath lab or stroke unit) are not treated as ambulance equipment; explicit equipment requirements such as an ICU ventilator remain hard eligibility filters.
