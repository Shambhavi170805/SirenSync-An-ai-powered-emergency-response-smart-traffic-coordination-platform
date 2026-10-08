# SirenSync — Cross-Module Integration Contracts & API Guide

**Producer:** Samriddhi (Hospital Intelligence & Bed Management Subsystem)  
**Consumers:** Shambhavi (Patient Experience + Intake), Nidhi (Ambulance Coordination)  
**Base URL:** `http://localhost:8000/api/v1`  
**Swagger UI:** `http://localhost:8000/docs`

---

## 1. Integration with Shambhavi (Patient Experience + Emergency Intake)

### A. Hospital Ranking Query
* **Method & Path:** `POST /api/v1/hospitals/rank`
* **Trigger:** Patient submits emergency coordinates and structured symptoms in Shambhavi's intake screen.
* **Request Payload:**
```json
{
  "emergencyId": "emg-9821a",
  "patientLocation": {
    "latitude": 12.9716,
    "longitude": 77.5946,
    "address": "MG Road Metro Station, Bangalore"
  },
  "emergencyType": "CARDIAC_ARREST",
  "priority": "P1_CRITICAL",
  "requiredBedType": "ICU",
  "requiredCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"]
}
```
* **Response (HTTP 200 OK):**
```json
{
  "emergencyId": "emg-9821a",
  "rankedHospitals": [
    {
      "hospitalId": "hosp-manipal-hal",
      "name": "Manipal Hospital HAL Airport Road",
      "location": {
        "latitude": 12.9592,
        "longitude": 77.6477,
        "address": "98, HAL Old Airport Rd, Kodihalli, Bengaluru"
      },
      "contactNumber": "+91-80-2502-4444",
      "compositeScore": 0.887,
      "rank": 1,
      "isEligible": true,
      "breakdown": {
        "distanceKm": 5.92,
        "distanceScore": 0.803,
        "capabilityMatchScore": 1.0,
        "matchedCapabilities": ["CARDIAC_CATH_LAB", "ICU_VENTILATOR"],
        "missingCapabilities": [],
        "trafficCongestionFactor": 1.15,
        "trafficScore": 0.87,
        "bedAvailabilityScore": 1.0,
        "availableBedsCount": 5,
        "explanation": "Distance: 5.92 km (score: 0.8). Capability Match: 100% (2/2 matched). Traffic: Moderate arterial traffic (+15% delay) (delay factor: 1.15). Bed Availability: 5 ICU beds available."
      },
      "bedSummary": {
        "ICU": { "available": 5, "reserved": 2, "occupied": 1, "total": 8 }
      }
    }
  ],
  "weightsApplied": {
    "distance": 0.3,
    "capability": 0.35,
    "traffic": 0.2,
    "bedAvailability": 0.15
  },
  "totalHospitalsEvaluated": 5,
  "eligibleHospitalsCount": 4
}
```

---

### B. Hospital Selection & Bed Locking
* **Method & Path:** `POST /api/v1/emergencies/{emergency_id}/select-hospital`
* **Trigger:** Patient taps on their chosen hospital from the ranked list in Shambhavi's UI.
* **Request Payload:**
```json
{
  "selectedHospitalId": "hosp-manipal-hal",
  "requiredBedType": "ICU"
}
```
* **Response (HTTP 201 Created):**
```json
{
  "status": "SUCCESS",
  "emergencyId": "emg-9821a",
  "hospitalId": "hosp-manipal-hal",
  "reservation": {
    "reservationId": "res-f4219a10",
    "bedId": "bed-hosp-manipal-hal-icu-01",
    "bedNumber": "ICU-01",
    "bedType": "ICU",
    "status": "RESERVED",
    "reservedAt": "2026-10-08T18:15:30Z"
  },
  "coordinatingHospital": {
    "hospitalId": "hosp-manipal-hal",
    "hospitalName": "Manipal Hospital HAL Airport Road",
    "contactNumber": "+91-80-2502-4444",
    "address": "98, HAL Old Airport Rd, Kodihalli, Bengaluru",
    "dispatchStatus": "AMBULANCE_COORDINATION_INITIATED"
  },
  "message": "Bed reserved securely. Hospital is now the coordinating authority."
}
```
* **Conflict Handling (HTTP 409 Conflict):**
  If concurrent requests claimed the last bed:
```json
{
  "detail": "Resource conflict: All ICU beds at 'Manipal Hospital HAL Airport Road' were locked by concurrent requests."
}
```

---

## 2. Integration with Nidhi (Ambulance Coordination & Real-Time Tracking)

### Machine-Readable Rerouting Event
When the Hospital Intelligence subsystem executes a priority reassignment under the **40% route-progress prototype policy**, it generates this exact event structure:

* **Event Type:** `BED_REASSIGNMENT_REROUTE`
* **Event Payload:**
```json
{
  "eventType": "BED_REASSIGNMENT_REROUTE",
  "eventId": "evt-reassign-8f12cb41",
  "emergencyId": "emg-displaced-001",
  "previousHospitalId": "hosp-manipal-hal",
  "previousBedId": "bed-hosp-manipal-hal-icu-01",
  "newHospitalId": "hosp-apollo-bg",
  "newBedId": null,
  "displacingEmergencyId": "emg-displacing-002",
  "displacingPriority": "P1_CRITICAL",
  "displacedPriority": "P3_URGENT",
  "reason": "HIGHER_PRIORITY_EMERGENCY",
  "routeProgress": 25.0,
  "threshold": 40.0,
  "status": "REROUTE_REQUIRED",
  "timestamp": "2026-10-08T18:20:00Z"
}
```

### Action Required by Nidhi's Ambulance Subsystem:
1. Verify `emergencyId` matches active ambulance dispatch.
2. Update destination hospital to `newHospitalId` (`hosp-apollo-bg`).
3. Re-calculate routing path to the new hospital.
4. Notify driver UI and stream live coordinates to patient.
