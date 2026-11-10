"""Sample/webcam/IP stream workers and annotated MJPEG output for the module UI."""

import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np

from ai_traffic.registered_corridor.plate_reader import PlateReader
from ai_traffic.registered_corridor.registry import normalize_plate
from ai_traffic.registered_corridor.synthetic_camera import SyntheticRoadCamera


class CameraHub:
    def __init__(self, cameras: list[dict], plate_reader: PlateReader,
                 on_plate: Callable[[str, str, str, float, str], None],
                 max_association_distance_m: float = 180):
        self.cameras = {item["camera_id"]: item for item in cameras}
        self.plate_reader = plate_reader
        self.on_plate = on_plate
        self.max_association_distance_m = max_association_distance_m
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lock = threading.RLock()
        self._frames: dict[str, np.ndarray] = {}
        self._statuses = {camera_id: "STARTING" for camera_id in self.cameras}
        self._candidate_reads: dict[tuple[str, str], tuple[float, int, float]] = {}
        self._last_attempts: dict[tuple[str, str], float] = {}
        self._last_results: dict[tuple[str, str], bool] = {}
        self._synthetic = {
            camera_id: SyntheticRoadCamera(camera_id, item.get("junction_id", "UNASSIGNED"))
            for camera_id, item in self.cameras.items() if item.get("source") == "synthetic"
        }

    def assign_route_junctions(self, junctions: list[dict]) -> None:
        """Map each configured feed to its nearest junction on the selected route."""
        if not junctions:
            return
        for camera_id, camera in self.cameras.items():
            camera_lat, camera_lng = camera.get("lat"), camera.get("lng")
            if camera_lat is None or camera_lng is None:
                url = str(camera.get("url", ""))
                network_feed = url.lower().startswith(("rtsp://", "http://", "https://"))
                local_index = url.isdigit()
                if camera.get("source") != "synthetic" and (network_feed or not local_index):
                    selected = None
                else:
                    # Only local webcam/demo feeds can use the route entry when no
                    # real camera coordinates have been configured.
                    selected = junctions[0]
            else:
                selected = min(junctions, key=lambda junction: self._distance(
                    float(camera_lat), float(camera_lng), junction["lat"], junction["lng"]
                ))
                if self._distance(float(camera_lat), float(camera_lng), selected["lat"], selected["lng"]) > self.max_association_distance_m:
                    selected = None
            with self._lock:
                camera["junction_id"] = selected["junction_id"] if selected else None
                if selected is None and camera.get("source") != "synthetic":
                    self._statuses[camera_id] = "NO_NEARBY_ROUTE_JUNCTION"
            if camera_id in self._synthetic and selected:
                self._synthetic[camera_id].junction_id = selected["junction_id"]

    @staticmethod
    def _distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        import math
        radius = 6_371_000
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        value = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))

    def start(self) -> None:
        self._stop.clear()
        for camera_id in self.cameras:
            thread = threading.Thread(target=self._run_camera, args=(camera_id,), daemon=True, name=f"plate-camera-{camera_id}")
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=2)
        self._threads.clear()

    def dispatch_demo(self, camera_id: str, plate: str) -> bool:
        camera = self._synthetic.get(camera_id)
        if not camera:
            return False
        camera.dispatch(plate)
        return True

    def _run_camera(self, camera_id: str) -> None:
        camera = self.cameras[camera_id]
        synthetic = self._synthetic.get(camera_id)
        capture = None
        last_scan = 0.0
        last_sample_plate = 0.0
        while not self._stop.is_set():
            if synthetic:
                frame, sample_plate = synthetic.read()
                status = "SIMULATED_SAMPLE"
            else:
                if capture is None or not capture.isOpened():
                    url = camera.get("url", "0")
                    target = int(url) if isinstance(url, str) and url.isdigit() else url
                    capture = cv2.VideoCapture(target)
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                ok, frame = capture.read() if capture else (False, None)
                sample_plate = None
                if not ok:
                    status = "CONNECTION_FAILED"
                    with self._lock:
                        self._statuses[camera_id] = status
                    if capture:
                        capture.release()
                        capture = None
                    self._stop.wait(2)
                    continue
                status = "CONNECTED"
            annotated = frame.copy()
            with self._lock:
                junction_id = camera.get("junction_id")
            now = time.monotonic()
            if synthetic and sample_plate and junction_id and now - last_sample_plate > 2:
                # The built-in feed supplies its drawn plate as deterministic sample metadata.
                # Real feeds always go through OCR below.
                self.on_plate(camera_id, junction_id, sample_plate, 99.0, "SYNTHETIC_SAMPLE")
                last_sample_plate = now
            elif not synthetic and now - last_scan >= .75:
                last_scan = now
                reads_by_plate = {}
                for read in self.plate_reader.scan(frame):
                    plate = normalize_plate(read.text)
                    if not plate:
                        continue
                    if plate not in reads_by_plate or read.confidence > reads_by_plate[plate].confidence:
                        reads_by_plate[plate] = read
                observed_keys = {(camera_id, plate) for plate in reads_by_plate}
                for key in [key for key in self._candidate_reads if key[0] == camera_id and key not in observed_keys]:
                    self._candidate_reads.pop(key, None)
                for plate, read in reads_by_plate.items():
                    read_key = (camera_id, plate)
                    previous = self._candidate_reads.get(read_key)
                    if previous and now - previous[0] <= 2.5:
                        count = previous[1] + 1
                        confidence = (previous[2] * previous[1] + read.confidence) / count
                    else:
                        count, confidence = 1, read.confidence
                    self._candidate_reads[read_key] = (now, count, confidence)
                    verified = self._last_results.get(read_key, False)
                    if junction_id and count >= 2 and now - self._last_attempts.get(read_key, 0) >= 3:
                        result = self.on_plate(camera_id, junction_id, plate, confidence, "CAMERA_OCR")
                        verified = bool(result.get("verified"))
                        self._last_attempts[read_key] = now
                        self._last_results[read_key] = verified
                    annotated = self.plate_reader.annotate(annotated, read, verified)
            with self._lock:
                self._frames[camera_id] = annotated
                self._statuses[camera_id] = status if junction_id or synthetic else "NO_NEARBY_ROUTE_JUNCTION"
            self._stop.wait(.04)
        if capture:
            capture.release()

    def get_status(self) -> dict:
        with self._lock:
            return {camera_id: {
                "camera_id": camera_id,
                "junction_id": self.cameras[camera_id].get("junction_id"),
                "source": self.cameras[camera_id].get("source", "camera"),
                "status": status,
            }
                    for camera_id, status in self._statuses.items()}

    def mjpeg(self, camera_id: str):
        while not self._stop.is_set():
            with self._lock:
                frame = self._frames.get(camera_id)
            if frame is None:
                frame = np.zeros((480, 800, 3), dtype=np.uint8)
                cv2.putText(frame, "WAITING FOR CAMERA", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, .8, (200, 200, 200), 2)
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
            time.sleep(.08)
