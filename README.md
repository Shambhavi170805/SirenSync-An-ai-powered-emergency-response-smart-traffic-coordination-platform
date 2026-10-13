# SirenSync: AI-Traffic / Green Corridor

An AI-powered pre-emptive green corridor module for emergency vehicles, built with YOLOv10, EasyOCR and FastAPI.

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

> **Note**: `easyocr` (~500 MB including PyTorch) will be downloaded on first install. It runs on CPU — no GPU required.

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

### 4. Set Camera URLs in `config.yaml`
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

The system clears traffic lights ahead of an approaching ambulance in 6 steps:

1. **Camera**: A video stream from an intersection camera (or the built-in demo video loop) reads road traffic in real time.
2. **YOLO Vehicle Detection**: YOLOv10 scans each frame and draws a bounding box around every vehicle.
3. **ANPR (Automatic Number Plate Recognition)**: For each vehicle box, the system crops the lower portion (the plate area) and runs EasyOCR to read the plate text. The raw text is normalised (uppercase, symbols removed, common OCR confusions fixed) and compared against the **ambulance registry** (`sample_data/ambulance_registry.json`). An exact match is tried first; if that fails, a fuzzy match allowing 1 character difference is tried. A match in **2 consecutive reads within 2 seconds** confirms the ambulance — this is the **primary detection method**.
4. **Beacon / Colour Backup**: If ANPR is unavailable or returns no match, the existing flashing red/blue beacon heuristic is tried as a backup. Custom YOLO ambulance weights (if supplied) are also used here.
5. **Green Corridor**: Once confirmed, only the **next junction ahead** on the active route turns GREEN. When the ambulance crosses, the signal holds green briefly, shows amber, then returns to RED.
6. **Dashboard**: A browser dashboard shows the live camera feed, signal states, real-time event log (including the matched plate and detection method), and a map with the ambulance marker.

---

## 📁 File Jobs (One Sentence Each)

- **`ai_traffic/main.py`**: Runs the FastAPI web server, WebSocket event stream, and in-memory event storage.
- **`ai_traffic/camera.py`**: Captures frames from cameras or generates the synthetic demo traffic video (including a vehicle with a readable sample plate).
- **`ai_traffic/detector.py`**: Runs YOLO, then ANPR (EasyOCR + plate matching), then falls back to the flashing beacon heuristic, confirming detections across consecutive frames.
- **`ai_traffic/plates.py`**: Loads the ambulance registry, normalises plate text, and performs exact + fuzzy plate matching.
- **`ai_traffic/signals.py`**: Controls junction traffic lights (RED → GREEN → HOLD → AMBER → RED) and provides signal adapters.
- **`ai_traffic/route.py`**: Calculates Haversine distance from the ambulance to upcoming junctions and triggers the 200 m pre-emption.
- **`config.yaml`**: Stores intersection locations, trigger distances, camera settings, ANPR confidence thresholds, and safety timeout values.
- **`ai_traffic/static/index.html`**: The single-page dashboard displaying maps, live video, signal states, and event logs.
- **`sample_data/ambulance_registry.json`**: Registry of authorised ambulance plates (plate, ambulance_id, operator, type, active flag).
- **`sample_data/generate_plate_image.py`**: One-time script that generates a JPEG of a sample plate for testing OCR.
- **`tests/test_core.py`**: Tests for signal transitions, the 200 m trigger, the health API, and ANPR plate normalisation / fuzzy matching.

---

## 🔌 Integration

### Connecting the Registry to the Ambulance Module's API

The `load_registry()` function in `ai_traffic/plates.py` currently reads from a local JSON file. To connect it to your teammates' Ambulance Coordination module:

1. Replace the body of `load_registry()` with an HTTP GET to the Ambulance module's endpoint, e.g.:
   ```python
   import requests
   def load_registry():
       resp = requests.get("http://ambulance-module/api/active-fleet")
       return resp.json()
   ```
2. The JSON format must stay the same: a list of objects with `plate`, `ambulance_id`, `active`, etc.
3. Set `only_dispatched_plate: true` in `config.yaml` to ensure only the ambulance currently assigned to the active route can trigger green.

### Connecting a Real ANPR Camera Stream

1. In `config.yaml`, change the camera `url` from `"demo"` to your RTSP stream:
   ```yaml
   url: "rtsp://user:pass@192.168.1.100:554/stream"
   ```
2. If the camera has a built-in ANPR output (many do), skip EasyOCR and call `match_plate()` directly with the camera's plate string.
3. Adjust `anpr_confidence_threshold` in `config.yaml` to match your camera's OCR accuracy.

### Other Integration Points

- **Route Provider**: POST to `http://localhost:8000/route` with the ambulance ID and waypoint list.
- **Real Signal Controller**: In `.env`, set `SIGNAL_CONTROLLER_TYPE=real`. Requires Smart City Traffic Police hardware clearance.
- **Event Consumers**: Connect to `ws://localhost:8000/ws/events` to receive `AMBULANCE_DETECTED` and `SIGNAL_CHANGED` JSON notifications (plate, ambulance_id, method, confidence, camera_id, junction_id, timestamp).

---

## ⚠️ Limitations

- **No Government Vahan Database Access**: The ambulance registry is the platform's own local JSON list (or an API you configure). It has no connection to the national Vahan vehicle database or MoRTH records.
- **OCR Accuracy Drops in Hard Conditions**: EasyOCR accuracy is significantly reduced at night, with motion blur, sharp angles, rain/glare, or dirty, damaged, or non-standard (fancy font) plates.
- **No Real Signal Control**: Physical signal pre-emption requires municipal Traffic Police authorization and certified hardware controller access.
- **No Government Camera Access**: Uses simulated video or user-provided RTSP streams; no access to government CCTV or ANPR infrastructure.
- **Default YOLO COCO Classes**: Standard COCO models have no `ambulance` class; the beacon/colour heuristic is the YOLO-based fallback unless custom fine-tuned weights are supplied.
- **Registry Must Be Kept Current**: If an ambulance's plate changes or it is decommissioned, the registry must be updated manually (or the API must reflect it); stale entries can cause false positives or missed detections.
