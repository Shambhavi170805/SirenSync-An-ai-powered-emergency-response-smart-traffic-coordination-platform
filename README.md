# SirenSync: AI-Traffic / Green Corridor

An AI-powered pre-emptive green corridor module for emergency vehicles, built with YOLOv10 and FastAPI.

---

## 🚀 How to Run

### 1. Create and Activate Virtual Environment
```bash
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Add Google Maps Key to `.env`
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Open `.env` and paste your key (optional &mdash; if omitted, an interactive vector map appears):
```ini
GOOGLE_MAPS_API_KEY=YOUR_API_KEY_HERE
SIGNAL_CONTROLLER_TYPE=simulated
```

### 4. Set Camera URLs in `ai_traffic/config.yaml`
By default, `url: "demo"` uses the built-in simulated traffic video. Replace with `"0"` for webcam or `"rtsp://..."` for an IP camera.

### 5. Run the Server
```bash
uvicorn ai_traffic.main:app --reload
```

### 6. Open Dashboard
Open your browser at:
👉 **http://localhost:8000**

---

## 💡 How It Works (Explained in Simple English)

The system clears traffic lights ahead of an approaching ambulance in 5 simple steps:

1. **Camera**: A video stream from an intersection camera (or a built-in demo video loop) reads road traffic in real time.
2. **Detector**: YOLOv10 scans each frame. If it spots an ambulance for 3 consecutive frames, it confirms the detection. If custom weights are missing, it uses a flashing emergency beacon light detector.
3. **Route**: The route coordinator tracks the ambulance's GPS coordinates and computes the distance to the next intersection ahead.
4. **Signals**: When the ambulance gets within 200 meters of an intersection (or the camera sees it), the signal turns **GREEN**. When the ambulance crosses, it holds green for 5 seconds, shows a short amber light, and returns to **RED**.
5. **Dashboard**: A browser dashboard shows the live camera feed, signal status, real-time event log, and Google Maps with the moving ambulance marker.

---

## 📁 File Jobs (One Sentence Each)

- **`ai_traffic/main.py`**: Runs the FastAPI web server, WebSocket event stream, and in-memory event storage.
- **`ai_traffic/camera.py`**: Captures frames from cameras or generates the synthetic demo traffic video.
- **`ai_traffic/detector.py`**: Runs YOLOv10 and the flashing beacon heuristic, confirming detections across 3 consecutive frames.
- **`ai_traffic/signals.py`**: Controls junction traffic lights (RED $\rightarrow$ GREEN $\rightarrow$ HOLD $\rightarrow$ AMBER $\rightarrow$ RED) and provides signal adapters.
- **`ai_traffic/route.py`**: Calculates Haversine distance from the ambulance to upcoming junctions and triggers the 200m pre-emption.
- **`ai_traffic/config.yaml`**: Stores intersection locations, trigger distances, camera settings, and safety timeout values.
- **`ai_traffic/static/index.html`**: The single-page dashboard displaying Google Maps, live video, signal states, and logs.
- **`sample_data/sample_route.json`**: Contains sample GPS route points for testing the ambulance corridor.
- **`tests/test_core.py`**: Automated tests that verify signal transitions, the 200m trigger logic, and the health API.

---

## 🔌 Integration

When connecting this module with your teammates' SirenSync modules, only change settings &mdash; no code changes required:

1. **Route Provider (Ambulance Coordination module)**:
   - Send HTTP POST requests to `http://localhost:8000/route` with the ambulance ID and waypoint list.
2. **Real Camera Feeds**:
   - In `ai_traffic/config.yaml`, set `url` to your RTSP stream (`rtsp://user:pass@ip:port/stream`) or USB camera index (`"0"`).
3. **Real Signal Controller**:
   - In `.env`, change `SIGNAL_CONTROLLER_TYPE=real`. Real signal hardware requires Smart City Traffic Police clearance.
4. **Patient / Hospital Dashboards**:
   - Connect to the WebSocket at `ws://localhost:8000/ws/events` to receive real-time `AMBULANCE_DETECTED` and `SIGNAL_CHANGED` JSON notifications.

---

## ⚠️ Limitations

- **No Real Signal Control**: Physical signal pre-emption requires municipal Traffic Police authorization and hardware controller access.
- **No Government Camera Access**: Uses simulated video or user-provided RTSP streams unless government feeds are configured.
- **Default YOLO COCO Classes**: Standard COCO models do not have an `ambulance` class, so the system uses a flashing beacon/color heuristic fallback unless custom fine-tuned ambulance weights are supplied.
