# SirenSync — Hospital Operations Dashboard Guide (Milestone 2)

**Author:** Samriddhi  
**Subsystem Responsibility:** Hospital Intelligence + Bed Management  
**Git Branch:** `feature/samriddhi-hospital`  
**Web Endpoint:** [http://localhost:8000/dashboard](http://localhost:8000/dashboard)  
**API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)  

---

## 1. Executive Summary & Architecture

The **Hospital Operations Dashboard** is an evaluator-presentable, real-time web interface built for hospital staff, medical coordinators, and evaluators. It visualizes the complete lifecycle of emergency hospital intelligence: from real-time bed inventories and incoming prioritized ambulance queues, to explainable multi-factor hospital selection and dynamic bed reassignments.

### Zero-Build Architecture
To ensure seamless evaluation and rapid local deployment, the dashboard employs a **Zero-Build, High-Performance Frontend Architecture**:
- **Host Engine:** Direct static file mounting via FastAPI (`StaticFiles(directory="frontend/hospital", html=True)`) at `/dashboard`.
- **Client Stack:** Native Modern ES6+ JavaScript modules and Tailwind CSS CDN.
- **Zero Build Artifacts:** No Node.js build pipeline, Webpack, or Vite bundling required. Simply run the FastAPI server, open a browser, and the dashboard is fully operational.
- **Transparent Refresh:** Built-in 10-second polling interval clearly labeled in the header (`Auto-refresh: 10s (Polling mode)`), ensuring full transparency without fake WebSocket claims.

---

## 2. Dashboard Layout & Component Breakdown

```
+--------------------------------------------------------------------------------------------------+
|  SIRENSYNC - HOSPITAL OPERATIONS INTELLIGENCE                                [Select Hospital v] |
|  Status: OPERATIONAL | Auto-refresh: 10s | Capabilities: [CARDIAC_CATH_LAB] [ICU_VENTILATOR]...   |
+--------------------------------------------------------------------------------------------------+
|  KEY PERFORMANCE INDICATORS (KPIs)                                                               |
|  [ Total Beds: 40 ]  [ Available: 18 ]  [ Reserved: 5 ]  [ Occupied: 17 ]  [ Active Queue: 5 ]   |
|  Capacity Progress Bar: Available (45%) | Reserved (12.5%) | Occupied (42.5%)                     |
+--------------------------------------------------------------------------------------------------+
|  BED CATEGORY INVENTORIES                                                                        |
|  [ICU Beds: 5 Avail / 8 Total] [Trauma Beds: 6 Avail / 10 Total] [Oxygen HDU: 8 Avail / 10 Total]|
+--------------------------------------------------------------------------------------------------+
|  NAVIGATION TABS:                                                                                |
|  [1. Bed Matrix]  [2. Emergency Queue]  [3. Active Reservations]  [4. Ranking Demo]  [5. Reassign]|
+--------------------------------------------------------------------------------------------------+
|  TAB 1: Interactive Bed Matrix                                                                   |
|  - Category & Status Filters                                                                     |
|  - Real-time Grid showing bed numbers, status colors, and "Mark Occupied" / "Discharge" buttons   |
+--------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Component Capabilities

### Tab 1: Interactive Bed Inventory Matrix
- **Visual Grid:** Categorized cards for every bed in the hospital (`ICU`, `TRAUMA_EMERGENCY`, `OXYGEN_HDU`, `GENERAL_WARD`, `PEDIATRIC_ICU`).
- **Real-Time State Badges:**
  - `AVAILABLE` (Emerald green) — Bed ready for patient assignment.
  - `RESERVED` (Indigo blue) — Bed locked atomically for an en-route ambulance.
  - `OCCUPIED` (Slate/Gray) — Bed occupied by an admitted patient.
  - `MAINTENANCE` (Amber/Orange) — Bed undergoing sterilization or servicing.
- **Resource Management Actions:** Hospital staff can toggle bed states directly (`PATCH /api/v1/hospitals/{hospital_id}/beds/{bed_id}/status`):
  - Click **"Mark Occupied"** when an incoming ambulance arrives and the patient is admitted.
  - Click **"Discharge"** to release an occupied bed back to available inventory.
  - Immediate toast notification and reactive KPI recalculation.

### Tab 2: Incoming Emergency Priority Queue
- **Live Inbound Roster:** Displays incoming ambulances routed to this hospital.
- **Priority Tiering:** Color-coded clinical urgency badges:
  - `P1_CRITICAL` (Red) — Life-threatening (e.g., cardiac arrest, major polytrauma).
  - `P2_EMERGENCY` (Orange) — High urgency, severe condition.
  - `P3_URGENT` (Amber) — Stable but requiring emergency facility admission.
  - `P4_STANDARD` (Blue) — Minor urgent care.
- **Transit Progress:** Visual progress bar showing estimated percentage of the route completed (`route_progress`).

### Tab 3: Active Bed Reservations Ledger
- **Atomic Locking Ledger:** Displays active and historical bed reservations created by the system.
- **Traceability:** Links `Reservation ID`, `Emergency ID`, assigned `Bed Number`, allocation timestamp, and current state.

### Tab 4: Evaluator Tool — Explainable 4-Factor Ranking Simulator
- **Interactive Demonstrator:** Allows evaluators to test how the backend computes hospital recommendations for arbitrary emergencies.
- **One-Click Presets:**
  - *Scenario A (Severe Cardiac Emergency):* Tests patient at Koramangala coordinates requesting `ICU` with `CARDIAC_CATH_LAB`.
  - *Highway Trauma Incident:* Tests patient on Bellary Road requesting `TRAUMA_EMERGENCY` with `TRAUMA_LEVEL_1`.
  - *Pediatric Respiratory Distress:* Tests patient requesting `PEDIATRIC_ICU`.
- **Explainable Metric Cards:**
  - **Overall Match Score:** Weighted composite score (0-100%).
  - **Distance:** Haversine distance in kilometers and proximity score.
  - **Capability Alignment:** List of matched clinical capabilities and penalty assessment for missing capabilities.
  - **Live Traffic Factor:** Simulated congestion multiplier via deterministic `MockTrafficProvider`.
  - **Bed Availability Buffer:** Usable bed count score.
  - **Transparent Narrative Text:** Human-readable reasoning explaining why the hospital ranked in its position.

### Tab 5: Evaluator Tool — Reassignment Policy & Audit Explorer
- **Policy Notice:** Prominently displays notice that the 40% route-progress threshold is a **configurable demonstration prototype policy**, not a medical or clinical protocol.
- **One-Click Reassignment Triggers:**
  - **Trigger Scenario C (Route: 25% < 40%):** Displacing P1 emergency arrives when existing P3 holds bed at 25% route completion.
    - *Outcome:* `REASSIGNMENT_APPROVED`.
    - Bed is atomically reassigned to the P1 critical emergency.
    - Emits machine-readable `BED_REASSIGNMENT_REROUTE` event contract for Nidhi's ambulance module.
  - **Trigger Scenario D (Route: 65% >= 40%):** Displacing P1 emergency arrives when existing P3 is at 65% route completion.
    - *Outcome:* `REASSIGNMENT_REJECTED`.
    - Bed reservation is retained by the inbound ambulance to prevent route disruption past the 40% threshold.
- **Machine-Readable Contract Viewer:** Displays formatted JSON payload of the reroute event ready for ambulance ingestion.
- **Complete Audit Trail:** Table showing historical displacement decisions, timestamps, and justification reasons.

---

## 4. Evaluator Verification Walkthrough (5-Minute Demo)

Follow these steps to demonstrate the full capabilities of Milestone 2:

### Step 1: Launch Application
1. In your terminal, initialize the seed data:
   ```bash
   python -m seed.demo_seed_data
   ```
2. Start the FastAPI server:
   ```bash
   python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
   ```
3. Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard) in Google Chrome or Microsoft Edge.

### Step 2: Hospital Selection & Overview Verification
1. Observe the top selector: Switch between **Manipal Hospital HAL Airport Road**, **Apollo Hospitals Bannerghatta Road**, and **Columbia Asia Hospital Hebbal**.
2. Notice how the KPI counters (Total, Available, Reserved, Occupied) update instantly.
3. Observe Columbia Asia Hospital: Note that its ICU available count is **0**, designed specifically to verify bed-exhaustion handling.

### Step 3: Test Interactive Bed Management Actions
1. Navigate to the **Bed Matrix** tab for Manipal Hospital.
2. Filter by `ICU` beds.
3. Find an `AVAILABLE` bed and click **"Mark Occupied"**.
4. Observe the instant UI feedback, toast notification, and KPI counter updating.
5. Find an `OCCUPIED` bed and click **"Discharge"**.
6. Observe the bed transition back to `AVAILABLE`.

### Step 4: Demonstrate Explainable Ranking (Scenario A)
1. Navigate to the **Ranking Demo** tab.
2. Click the preset button: **"Scenario A: Severe Cardiac (Cath Lab + ICU)"**.
3. Click **"Run Ranking Engine"**.
4. Review the top-ranked hospital (**Manipal Hospital HAL Airport Road**).
5. Inspect the 4-factor scoring breakdown:
   - Proximity: ~5.8 km
   - Capability: `CARDIAC_CATH_LAB` (100% matched)
   - Traffic: Normal multiplier (1.0)
   - Beds: Positive ICU buffer
6. Read the plain-language explanation generated by the engine.

### Step 5: Demonstrate 40% Route-Progress Reassignment (Scenarios C & D)
1. Navigate to the **Reassignment Audit** tab.
2. Review the prototype policy disclaimer banner.
3. Click **"Trigger Scenario C (Route: 25% < 40%)"**:
   - Status evaluates to **REASSIGNMENT_APPROVED**.
   - Note the emitted `BED_REASSIGNMENT_REROUTE` machine-readable JSON contract.
4. Click **"Trigger Scenario D (Route: 65% >= 40%)"**:
   - Status evaluates to **REASSIGNMENT_REJECTED**.
   - Notice the explanation stating the existing patient has exceeded 40% route progress and retains their allocation.
5. View the newly appended audit records in the table below.

---

## 5. Subsystem Ownership Boundary Notice

| Action / Interface | Subsystem Owner | Boundary Compliance |
|---|---|---|
| Hospital Operations Dashboard | **Samriddhi (Hospital Intelligence)** | **YES — Fully owned** |
| Bed Inventory & Status Management | **Samriddhi (Hospital Intelligence)** | **YES — Fully owned** |
| 4-Factor Ranking Demonstration Tool | **Samriddhi (Hospital Intelligence)** | **YES — Evaluator testbed only** |
| Reassignment Policy & Audit Explorer | **Samriddhi (Hospital Intelligence)** | **YES — Fully owned** |
| Patient Intake UI / Symptom Input | Shambhavi (Emergency Intake) | **NOT INCLUDED** (Consumes shared contracts only) |
| Ambulance Live GPS Map / Driver App | Nidhi (Ambulance Coordination) | **NOT INCLUDED** (Emits reroute JSON only) |
| Traffic Signal AI Camera / YOLO CV | Ishita Bisht (Traffic AI) | **NOT INCLUDED** (Consumes mock traffic factors only) |
