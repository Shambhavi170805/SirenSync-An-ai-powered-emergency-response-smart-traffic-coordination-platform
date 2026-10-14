"""Sample/webcam/IP stream workers and annotated MJPEG output for the module UI."""

import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np

from ai_traffic.registered_corridor.plate_reader import PlateReader
from ai_traffic.registered_corridor.synthetic_camera import SyntheticRoadCamera


class CameraHub:
    def __init__(self, cameras: list[dict], plate_reader: PlateReader,
                 on_plate: Callable[[str, str, str, float, str], None]):
        self.cameras = {item["camera_id"]: item for item in cameras}
        self.plate_reader = plate_reader
        self.on_plate = on_plate
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lock = threading.RLock()
        self._frames: dict[str, np.ndarray] = {}
        self._statuses = {camera_id: "STARTING" for camera_id in self.cameras}
        self._last_reads: dict[tuple[str, str], float] = {}
        self._verified_reads: set[tuple[str, str]] = set()
        self._synthetic = {
            camera_id: SyntheticRoadCamera(camera_id, item["junction_id"])
            for camera_id, item in self.cameras.items() if item.get("source") == "synthetic"
        }

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
        junction_id = camera["junction_id"]
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
            now = time.monotonic()
            if synthetic and sample_plate and now - last_sample_plate > 2:
                # The built-in feed supplies its drawn plate as deterministic sample metadata.
                # Real feeds always go through OCR below.
                self.on_plate(camera_id, junction_id, sample_plate, 99.0, "SYNTHETIC_SAMPLE")
                last_sample_plate = now
            elif not synthetic and now - last_scan >= .75:
                last_scan = now
                for read in self.plate_reader.scan(frame):
                    read_key = (camera_id, read.text)
                    verified = read_key in self._verified_reads
                    if now - self._last_reads.get(read_key, 0) >= 3:
                        result = self.on_plate(camera_id, junction_id, read.text, read.confidence, "CAMERA_OCR")
                        verified = bool(result.get("verified"))
                        if verified:
                            self._verified_reads.add(read_key)
                        self._last_reads[read_key] = now
                    annotated = self.plate_reader.annotate(annotated, read, verified)
            with self._lock:
                self._frames[camera_id] = annotated
                self._statuses[camera_id] = status
            self._stop.wait(.04)
        if capture:
            capture.release()

    def get_status(self) -> dict:
        with self._lock:
            return {camera_id: {"camera_id": camera_id, "junction_id": self.cameras[camera_id]["junction_id"], "status": status}
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
