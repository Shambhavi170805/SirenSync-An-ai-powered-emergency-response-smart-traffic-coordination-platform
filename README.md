# SirenSync — AI-Powered Emergency Response & Smart Traffic Coordination Platform

An AI-powered emergency healthcare platform connecting patient symptoms to the right ambulance and best-fit hospital, rather than just the nearest one. It also uses traffic and signal awareness to suggest optimized routes and demonstrate how AI-based traffic coordination can reduce ambulance transit time and improve emergency response.

---

## Team Ownership & Architecture

| Team Member | Subsystem Ownership | Core Deliverable |
|---|---|---|
| **Shambhavi** | Patient Experience + Emergency Intake | Patient intake UI, symptom input, patient hospital selection UI |
| **Samriddhi (ME)** | **Hospital Intelligence + Bed Management** | **Explainable 4-factor ranking, concurrency-safe bed locking, 40% route-progress prototype reassignment policy, hospital queue** |
| **Nidhi** | Ambulance Coordination + Real-Time Tracking | Ambulance fleet, driver workflow, live location streaming, reroute execution |
| **Ishita Bisht** | AI Traffic Detection + Green Corridor | Pretrained YOLO detector on sample footage, simulated traffic signal priority |

---

## Hospital Intelligence + Bed Management Subsystem (Milestones 1 & 2)

This subsystem provides the complete coordinating backend and operational intelligence dashboard for SirenSync:

1. **Deterministic 4-Factor Hospital Ranking Engine:**
   - **Distance:** Great-circle Haversine proximity.
   - **Capability Matching:** Clinical specialization alignment (Cath Lab, Trauma Level 1, ICU Ventilators, Stroke Units, etc.) to prevent secondary hospital transfers.
   - **Live Traffic Factor:** Deterministic congestion simulation via pluggable `MockTrafficProvider` (zero external API keys required).
   - **Bed Availability:** Live buffer calculation across bed categories (`ICU`, `TRAUMA_EMERGENCY`, `OXYGEN_HDU`, `GENERAL_WARD`, `PEDIATRIC_ICU`).
   - **Explainability:** Returns normalized scores, matched/missing capabilities, and transparent narrative text.

2. **Concurrency-Safe Transactional Bed Reservation (Atomic Compare-and-Swap):**
   - Eliminates race conditions at the database engine level using atomic conditional updates (`UPDATE beds SET status='RESERVED' WHERE status='AVAILABLE'`).
   - SQLite configured with Write-Ahead Logging (`WAL` mode) and busy timeout.
   - Backed by multi-threaded automated test verifying zero double-booking under concurrent load.

3. **40% Route-Progress Prototype Bed Reassignment Policy:**
   - Evaluates whether higher-priority emergencies can reassign reserved beds.
   - *Prototype Policy Notice:* The 40% route-progress threshold is a configurable prototype heuristic for demonstration; it does not constitute a clinical or medical protocol.
   - Emits a standardized `BED_REASSIGNMENT_REROUTE` machine-readable event for Nidhi's ambulance module.

4. **Hospital Operations Dashboard (Milestone 2):**
   - Zero-build modern web interface served directly via FastAPI at `/dashboard`.
   - Real-time KPI summaries, interactive bed matrix with status toggles ("Mark Occupied" / "Discharge").
   - Live inbound emergency priority queue (`P1` to `P4`) with route progress tracking.
   - Evaluator testbeds for 4-factor ranking and 1-click reassignment scenario triggers (Scenarios C & D).

---

## Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14.7)
- Zero external API keys or credentials needed for local development and evaluation.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
Seeds 5 Bengaluru hospitals (Manipal, Apollo, Fortis, Columbia Asia, Bowring) with realistic capabilities, beds, queue items, and coordinates:
```bash
python -m seed.demo_seed_data
```

### 4. Run the Application
```bash
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```
- **Hospital Operations Dashboard:** [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- System Status: [http://localhost:8000/](http://localhost:8000/)

---

## Running the Automated Test Suite

Run the full suite of 22 unit, integration, dashboard, and multi-threaded concurrency tests:
```bash
python -m pytest -v
```

### Test Suite Highlights:
- `tests/test_ranking.py`: Haversine calculation, capability filtering, bed count scoring, and explainable breakdowns.
- `tests/test_bed_concurrency.py`: 10-thread concurrent race condition test demonstrating that when 10 threads compete for 1 bed, exactly 1 wins and 9 fail cleanly with 409 Conflict.
- `tests/test_reassignment_policy.py`: Verifies reassignment triggers at 25% progress (< 40%) and rejects at 65% progress (>= 40%).
- `tests/test_api_integration.py`: End-to-end API walkthrough (Directory &rarr; Ranking &rarr; Hospital Selection &rarr; Bed Lock &rarr; Audit).
- `tests/test_dashboard_api.py`: Tests dashboard aggregation, inbound queue, reservations ledger, and bed status transitions.

---

## Evaluator Demo Scenarios

| Scenario | Description | Expected Outcome |
|---|---|---|
| **Scenario A (Normal Flow)** | Patient raises `P1_CRITICAL` cardiac emergency. | Manipal ranks #1 due to Cath Lab match; ICU bed locked atomically; coordinating hospital confirmed. |
| **Scenario B (Concurrency Race)** | 10 concurrent requests compete for 1 available ICU bed. | Exactly 1 reservation succeeds; 9 fail with 409 Conflict; database state remains consistent. |
| **Scenario C (Reassignment < 40%)** | P1 emergency arrives while P3 emergency holds bed with route progress at 25%. | Reassignment approved (25% < 40%); bed given to P1; `BED_REASSIGNMENT_REROUTE` event emitted for P3 ambulance. |
| **Scenario D (Reassignment >= 40%)** | P1 emergency arrives while P3 emergency holds bed with route progress at 65%. | Reassignment rejected (65% >= 40%); P3 retains bed to preserve journey stability. |

---

## Documentation Links

- [Hospital Operations Dashboard User Guide & Evaluator Script](file:///docs/DASHBOARD_GUIDE.md)
- [System Architecture & Concurrency Design](file:///docs/ARCHITECTURE.md)
- [Deterministic 4-Factor Ranking Algorithm](file:///docs/RANKING_ALGORITHM.md)
- [Cross-Module Integration Contracts & API Guide](file:///docs/INTEGRATION_CONTRACTS.md)
