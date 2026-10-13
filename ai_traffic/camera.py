"""
Camera ingestion module: reads camera streams or generates a built-in demo video.
"""

import threading
import time
import cv2
import numpy as np

# Global store for the latest camera frames
_latest_frames = {}
_lock = threading.Lock()


# Generates a realistic synthetic road frame with cars and an emergency ambulance
def generate_demo_frame(frame_counter: int) -> np.ndarray:
    frame = np.full((480, 640, 3), (45, 50, 45), dtype=np.uint8)

    # Draw dark road asphalt
    cv2.rectangle(frame, (180, 0), (460, 480), (40, 40, 40), -1)
    cv2.rectangle(frame, (0, 160), (640, 320), (40, 40, 40), -1)

    # Draw lane lines
    for y in range(0, 480, 40):
        cv2.line(frame, (320, y), (320, y + 20), (255, 255, 255), 2)

    # Animate civilian cars
    car_y1 = (frame_counter * 3) % 480
    cv2.rectangle(frame, (230, car_y1), (260, car_y1 + 45), (160, 160, 160), -1)

    # Animate ambulance every 100 frames
    amb_cycle = frame_counter % 200
    if amb_cycle < 120:
        amb_y = int(480 - (amb_cycle * 4.5))
        amb_x = 360

        # White vehicle body
        cv2.rectangle(frame, (amb_x - 20, amb_y - 35), (amb_x + 20, amb_y + 35), (245, 245, 245), -1)
        # Red side stripe & roof cross
        cv2.line(frame, (amb_x - 20, amb_y), (amb_x + 20, amb_y), (0, 0, 220), 3)
        cv2.line(frame, (amb_x - 6, amb_y - 8), (amb_x + 6, amb_y - 8), (0, 0, 220), 3)
        cv2.line(frame, (amb_x, amb_y - 14), (amb_x, amb_y - 2), (0, 0, 220), 3)

        # Flashing red and blue beacons on roof
        beacon_color1 = (0, 0, 255) if (frame_counter // 3) % 2 == 0 else (255, 80, 0)
        beacon_color2 = (255, 80, 0) if (frame_counter // 3) % 2 == 0 else (0, 0, 255)
        cv2.circle(frame, (amb_x - 10, amb_y - 20), 5, beacon_color1, -1)
        cv2.circle(frame, (amb_x + 10, amb_y - 20), 5, beacon_color2, -1)

    # Add timestamp and simulated badge
    cv2.putText(frame, "SIMULATED DEMO FEED", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 1)
    return frame


# Runs in a thread to continuously read frames from a camera or demo generator
def camera_worker_loop(cam_id: str, url: str):
    frame_count = 0
    cap = None

    if url != "demo":
        try:
            target = int(url) if url.isdigit() else url
            cap = cv2.VideoCapture(target)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as e:
            print(f"[CAM] Failed to open {cam_id} at {url}: {e}. Using demo feed.")
            cap = None

    while True:
        frame = None
        if cap is not None and cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.5)
                continue
        else:
            frame = generate_demo_frame(frame_count)
            frame_count += 1

        with _lock:
            _latest_frames[cam_id] = frame

        time.sleep(0.04)  # ~25 FPS


# Starts background reader threads for all cameras listed in config
def start_cameras(camera_configs: list):
    for cam in camera_configs:
        cam_id = cam.get("id", "CAM-1")
        url = cam.get("url", "demo")
        t = threading.Thread(target=camera_worker_loop, args=(cam_id, url), daemon=True)
        t.start()
        print(f"[CAM] Camera thread started for {cam_id} (Source: {url})")


# Gets the most recent frame for a camera in a thread-safe way
def get_camera_frame(cam_id: str) -> np.ndarray:
    with _lock:
        frame = _latest_frames.get(cam_id)
        if frame is not None:
            return frame.copy()
    return generate_demo_frame(0)


# Updates the annotated frame so the web stream shows bounding boxes
def set_annotated_frame(cam_id: str, frame: np.ndarray):
    with _lock:
        _latest_frames[cam_id] = frame


# Generates a multipart MJPEG JPEG byte stream for the browser
def get_mjpeg_stream(cam_id: str):
    while True:
        frame = get_camera_frame(cam_id)
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if ret:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.04)
