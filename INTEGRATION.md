# SirenSync: AI-Traffic / Green Corridor Integration Guide

This guide describes how to connect the **AI-Traffic / Green Corridor** module to the rest of the **SirenSync** platform:
1. **Upstream Ambulance Route Provider** (Ambulance Coordination & Tracking module)
2. **Real Camera Feeds** (Municipal Traffic Feeds / Roadside IP Cameras)
3. **Real Signal Controller** (Smart City TMC / Traffic Police NTCIP Gateway)
4. **Patient Intake & Hospital Dashboards** (Telemetry consumption & ETA updates)

> **Architectural Guarantee**: This module is designed so that final deployment **requires only configuration adjustments in `.env` and `config.yaml`**, with **zero code modifications**.

---

## 1. Connecting the Upstream Route Provider

When a patient selects a hospital and an ambulance is dispatched, the **Ambulance Coordination** module computes the optimal path and passes it to the Green Corridor.

### A. Initial Route Ingestion
Once the ambulance departs, the route provider sends a `POST` request to `/route`:

- **Endpoint**: `POST http://localhost:8000/route`
- **Headers**: `Content-Type: application/json`

#### Option 1: Direct Waypoint Payload (Recommended)
If your routing service has pre-calculated coordinates:
```json
{
  "ambulance_id": "AMB-BLR-402",
  "emergency_severity": "CRITICAL",
  "junctions": ["J-101", "J-102", "J-103"],
  "progress_percent": 0.0,
  "route_points": [
    { "lat": 12.9660, "lng": 77.5880, "speed_kmh": 40.0 },
    { "lat": 12.9716, "lng": 77.5946, "speed_kmh": 45.0 },
    { "lat": 12.9758, "lng": 77.6012, "speed_kmh": 42.0 },
    { "lat": 12.9812, "lng": 77.6085, "speed_kmh": 30.0 }
  ]
}
```

#### Option 2: Google Maps Origin & Destination
If you prefer this module to fetch the itinerary directly via Google Maps Directions API:
```json
{
  "ambulance_id": "AMB-BLR-402",
  "emergency_severity": "CRITICAL",
  "origin": "12.9660,77.5880",
  "destination": "12.9812,77.6085"
}
```

### B. Live GPS Breadcrumb Updates
As the ambulance moves in the real world, the vehicle's onboard GPS unit posts updates:

- **Endpoint**: `POST http://localhost:8000/route/progress`
```json
{
  "ambulance_id": "AMB-BLR-402",
  "progress_percent": 34.5,
  "current_lat": 12.9718,
  "current_lng": 77.5949
}
```

#### Python Upstream Snippet Example:
```python
import requests

def push_ambulance_telemetry(ambulance_id, progress_pct, lat, lng):
    url = "http://localhost:8000/route/progress"
    payload = {
        "ambulance_id": ambulance_id,
        "progress_percent": progress_pct,
        "current_lat": lat,
        "current_lng": lng
    }
    requests.post(url, json=payload, timeout=2.0)
```

---

## 2. Connecting Real Camera Feeds

To replace simulated synthetic feeds with physical traffic cameras:

### Edit `config.yaml`
Modify the `cameras` array in `config.yaml`:

```yaml
cameras:
  # Example 1: Physical RTSP IP Camera (H.264 / RTSP stream)
  - camera_id: "CAM-J1-NORTH"
    name: "MG Road North Approach - Hikvision PTZ"
    junction_id: "J-101"
    url: "rtsp://admin:TrafficPass2026@192.168.1.120:554/Streaming/Channels/101"
    is_simulated: false
    reconnect_interval_seconds: 5.0
    max_fps: 25
    location:
      lat: 12.97160
      lng: 77.59460
      address: "MG Road & Brigade Rd Intersection"

  # Example 2: Local USB/CSI Webcam (Index 0 or 1)
  - camera_id: "CAM-J2-CENTRAL"
    name: "Trinity Circle Local Lens"
    junction_id: "J-102"
    url: "0"  # String integer parsed as video capture index 0
    is_simulated: false
    reconnect_interval_seconds: 3.0
    max_fps: 30
    location:
      lat: 12.97580
      lng: 77.60120

  # Example 3: Recorded High-Definition Video File for Field Testing
  - camera_id: "CAM-J3-EAST"
    name: "Hospital Entry Recorded Test Run"
    junction_id: "J-103"
    url: "sample_data/sample_traffic.mp4"
    is_simulated: true
    reconnect_interval_seconds: 5.0
```

### Production Dropped-Frame & Network Protections:
- `reconnect_interval_seconds`: Number of seconds to wait before auto-reconnecting after dropped RTSP packets.
- `cv2.CAP_PROP_BUFFERSIZE = 1`: Internal buffer is clamped to 1 frame so stale frames are discarded, guaranteeing real-time inference without accumulated latency.

---

## 3. Connecting the Real Signal Controller

### Disclaimer & Architecture Scope
> **IMPORTANT**: Physical roadside traffic controllers require certified municipal access, hardware conflict monitors (CMU), and fail-safe protocols. The module provides a plug-and-play adapter interface.

### Step 1: Switch Controller in `.env`
Update `.env`:
```ini
# Change from "simulated" to "real"
SIGNAL_CONTROLLER_TYPE=real

# Municipal Smart City TMC Gateway Endpoint
REAL_CONTROLLER_ENDPOINT=https://tmc-api.smartcity.gov.in/v1/emergency-preemption
REAL_CONTROLLER_API_KEY=municipal_secret_bearer_token_xyz
REAL_CONTROLLER_TIMEOUT_SECONDS=4.0
```

### What Happens Behind the Scenes:
The `RealSignalController` automatically packages each signal request and dispatches an authenticated HTTP POST payload to the municipal TMC:

```json
{
  "junctionId": "J-101",
  "requestedPhase": "GREEN",
  "preemptionType": "EMERGENCY_VEHICLE",
  "triggerReason": "CAMERA_VISION_DETECTION",
  "vehicleId": "AMB-BLR-402",
  "timestamp": "2026-10-11T05:32:00.120Z"
}
```

If the TMC endpoint is temporarily unreachable or times out, the adapter logs a fallback warning and keeps the system operational without crashing.

---

## 4. Connecting Patient & Hospital Dashboards

The patient intake dashboard and hospital emergency ranking dashboard can consume real-time corridor telemetry via **WebSocket** or **REST polling**.

### A. Real-Time WebSocket Feed (`/ws/events`)

Connect your frontend or backend microservices to:
`ws://localhost:8000/ws/events`

#### JavaScript / React Integration:
```javascript
const socket = new WebSocket("ws://localhost:8000/ws/events");

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.event_type) {
    case "SIGNAL_CHANGED":
      console.log(`Signal at ${data.junction_id} turned ${data.state} for ${data.ambulance_id}`);
      break;
    case "AMBULANCE_DETECTED":
      console.log(`Camera ${data.camera_id} confirmed ambulance with ${data.confidence * 100}% confidence`);
      break;
    case "ROUTE_UPDATED":
      console.log(`Ambulance progress: ${data.progress_percent}%, Next junction: ${data.next_junction_id}`);
      break;
    case "CONFLICT_DETECTED":
      console.warn(`Traffic conflict at ${data.junction_id}: prioritizing ${data.prioritized_ambulance}`);
      break;
  }
};
```

### B. REST Endpoints for Dashboards

| Method | Endpoint | Description | Consuming Module |
|---|---|---|---|
| `GET` | `/junctions` | Returns all junctions, active signal phase, and queued ambulances. | Hospital Command Center |
| `GET` | `/events?limit=50` | Query persistent audit events. | Audit & Analytics Module |
| `GET` | `/health` | Verify module health, camera statuses, and detector state. | DevOps / Gateway Health |
| `GET` | `/video_feed/{camera_id}` | Live MJPEG stream for embedding in emergency operations video walls. | Hospital & TMC Operations |

---

## 5. Conflict Resolution Behavior

When two ambulances approach the same intersection:
- The `ConflictManager` analyzes emergency triage severity:
  - `CRITICAL` (Cardiac arrest / polytrauma) weight: **100**
  - `HIGH` (Severe respiratory / stroke) weight: **50**
  - `MODERATE` (Urgent non-life-threatening) weight: **20**
- Plus proximity bonus (`50 - ETA * 0.5`) and anti-starvation aging bonus.
- The higher-scoring vehicle is granted the green corridor; the other vehicle is queued and immediately serviced once the intersection clears.
- Emits `CONFLICT_DETECTED` event to inform the hospital coordination room of expected delays.
