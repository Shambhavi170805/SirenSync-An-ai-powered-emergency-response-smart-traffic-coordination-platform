"""
Object detection module: runs YOLOv10 with emergency strobe heuristic and 3-frame confirmation.
"""

from pathlib import Path
import cv2
import numpy as np
import yaml
try:
    import easyocr
except ImportError:
    easyocr = None
from .plates import load_registry, normalise_plate, match_plate, fallback_plate_crop

# Tracks consecutive detection counts per camera
_consecutive_counts = {}
_model = None
_has_custom_weights = False
# Load configuration and ambulance registry
with open(Path(__file__).parents[1] / 'config.yaml', 'r', encoding='utf-8') as f:
    _config = yaml.safe_load(f)
_registry = load_registry()
# Initialise EasyOCR if available
if easyocr:
    _ocr_reader = easyocr.Reader(['en'], gpu=False)
else:
    _ocr_reader = None
# Track consecutive plate matches per camera
_plate_match_counts = {}



# Initializes YOLOv10 or logs the fallback heuristic warning
def init_detector(weights_path: str = "yolov10n_ambulance.pt"):
    global _model, _has_custom_weights
    try:
        from ultralytics import YOLO
        if Path(weights_path).exists():
            _model = YOLO(weights_path)
            _has_custom_weights = True
            print(f"[DETECTOR] Loaded fine-tuned ambulance weights: {weights_path}")
        else:
            print("[INFO] Ambulance weights not found. Falling back to vehicle detection + beacon color heuristic.")
            _model = YOLO("yolov10n.pt")
            _has_custom_weights = False
    except Exception as e:
        print(f"[INFO] YOLO not loaded ({e}). Operating in standalone strobe beacon heuristic mode.")
        _model = None
        _has_custom_weights = False


# Checks vehicle crop for flashing red and blue beacon lights
def check_beacon_heuristic(crop: np.ndarray) -> bool:
    if crop is None or crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
        return False

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    # Red strobe mask
    red1 = cv2.inRange(hsv, np.array([0, 100, 120]), np.array([10, 255, 255]))
    red2 = cv2.inRange(hsv, np.array([170, 100, 120]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(red1, red2)

    # Blue strobe mask
    blue_mask = cv2.inRange(hsv, np.array([100, 100, 120]), np.array([130, 255, 255]))

    # Check for concentrated red/blue light pixels near the roof
    top_crop = int(crop.shape[0] * 0.4)
    beacon_pixels = np.count_nonzero(red_mask[:top_crop, :]) + np.count_nonzero(blue_mask[:top_crop, :])
    return beacon_pixels > 12


# Detects ambulance in a frame and checks N consecutive frame confirmation
def detect_ambulance(frame: np.ndarray, cam_id: str, conf_threshold: float = 0.50, confirm_frames: int = 3):
    annotated = frame.copy()
    ambulance_seen = False
    best_conf = 0.0
    best_box = None   # [x1, y1, x2, y2] or None

    # --- Step 1: YOLO vehicle detection ---
    if _model is not None:
        try:
            results = _model(frame, conf=conf_threshold, verbose=False)
            boxes = results[0].boxes
            for b in boxes:
                cls_id = int(b.cls[0])
                conf = float(b.conf[0])
                xyxy = [int(v) for v in b.xyxy[0].tolist()]

                # Custom model: class 0 is ambulance
                if _has_custom_weights and cls_id == 0:
                    ambulance_seen = True
                    best_conf = conf
                    best_box = xyxy
                    break
                # Base COCO model: check vehicles for beacon lights
                elif not _has_custom_weights and cls_id in [2, 5, 7]:
                    x1, y1, x2, y2 = xyxy
                    crop = frame[max(0, y1):min(frame.shape[0], y2),
                                 max(0, x1):min(frame.shape[1], x2)]
                    if check_beacon_heuristic(crop):
                        ambulance_seen = True
                        best_conf = conf
                        best_box = xyxy
                        break
                    # Save the last vehicle box for ANPR even if beacon check failed
                    best_box = xyxy
        except Exception:
            pass

    # --- Step 2: ANPR plate recognition (primary method) ---
    # Only runs when a vehicle box was found and OCR is available
    if not ambulance_seen and _ocr_reader and best_box is not None:
        try:
            plate_crop = fallback_plate_crop(best_box, frame)
            ocr_results = _ocr_reader.readtext(plate_crop, detail=0)
            for txt in ocr_results:
                norm = normalise_plate(txt)
                registry_match = match_plate(norm, _registry)
                if registry_match:
                    ambulance_seen = True
                    best_conf = _config.get("detection", {}).get("anpr_confidence_threshold", 0.60)
                    _plate_match_counts[cam_id] = _plate_match_counts.get(cam_id, 0) + 1
                    break
        except Exception:
            pass

    # --- Step 3: Fallback strobe/beacon scan (last resort) ---
    if not ambulance_seen:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.bitwise_or(
            cv2.inRange(hsv, np.array([0, 120, 140]), np.array([10, 255, 255])),
            cv2.inRange(hsv, np.array([100, 120, 140]), np.array([130, 255, 255]))
        )
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if 20 < cv2.contourArea(cnt) < 1000:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                best_box = [
                    max(0, bx - 25), max(0, by - 15),
                    min(frame.shape[1], bx + bw + 25),
                    min(frame.shape[0], by + bh + 50)
                ]
                ambulance_seen = True
                best_conf = 0.75
                break

    # --- Update consecutive detection counter ---
    count = _consecutive_counts.get(cam_id, 0)
    if ambulance_seen:
        count += 1
    else:
        count = 0
    _consecutive_counts[cam_id] = count

    # Confirmed only after N consecutive frames
    is_confirmed = (count >= confirm_frames)

    # Draw bounding box on annotated frame
    if best_box is not None:
        x1, y1, x2, y2 = best_box
        box_color = (0, 0, 255) if is_confirmed else (0, 165, 255)
        label = "AMBULANCE [CONFIRMED]" if is_confirmed else f"AMBULANCE [{count}/{confirm_frames}]"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
        cv2.putText(annotated, label, (x1, max(15, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

    return is_confirmed, round(best_conf, 2), annotated
