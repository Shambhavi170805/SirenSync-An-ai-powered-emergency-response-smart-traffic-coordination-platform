"""
Multi-source Camera Stream Manager.
Supports RTSP, HTTP/MJPEG, local webcam indices, video files, and synthetic test streams.
Handles per-camera worker threads, dropped frame mitigations, automatic reconnects,
and thread-safe frame access for MJPEG browser feeds.
"""

import threading
import time
from typing import Dict, Generator, List, Optional, Tuple
import cv2
import numpy as np

from ai_traffic.camera.synthetic_feed import SyntheticTrafficFeed
from ai_traffic.core.config import CameraConfig
from ai_traffic.core.logger import logger


class CameraSource:
    """
    Manages an individual camera feed in a dedicated background thread.
    """

    def __init__(self, config: CameraConfig):
        self.config = config
        self.camera_id = config.camera_id
        self.junction_id = config.junction_id
        self.url = config.url
        self.is_simulated = config.is_simulated or config.url.lower() == "demo"
        self.reconnect_interval = config.reconnect_interval_seconds
        self.max_fps = config.max_fps

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._latest_raw_frame: Optional[np.ndarray] = None
        self._latest_annotated_frame: Optional[np.ndarray] = None
        self._status = "INITIALIZING"
        self._fps_actual = 0.0
        self._synthetic_feed: Optional[SyntheticTrafficFeed] = None
        self._capture: Optional[cv2.VideoCapture] = None

    @property
    def status(self) -> str:
        return self._status

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name=f"CameraThread-{self.camera_id}",
            daemon=True
        )
        self._thread.start()
        logger.info(f"Started camera thread for {self.camera_id} (Target: {self.url})")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._cleanup_capture()
        self._status = "STOPPED"
        logger.info(f"Stopped camera stream {self.camera_id}")

    def trigger_demo_ambulance(self) -> None:
        """Triggers simulated ambulance on synthetic feeds."""
        if self._synthetic_feed:
            self._synthetic_feed.trigger_ambulance()

    def get_latest_frame(self, annotated: bool = True) -> Optional[np.ndarray]:
        with self._lock:
            if annotated and self._latest_annotated_frame is not None:
                return self._latest_annotated_frame.copy()
            if self._latest_raw_frame is not None:
                return self._latest_raw_frame.copy()
            return None

    def update_annotated_frame(self, frame: np.ndarray) -> None:
        with self._lock:
            self._latest_annotated_frame = frame

    def _open_capture(self) -> bool:
        if self.is_simulated or self.url.lower() == "demo":
            self._synthetic_feed = SyntheticTrafficFeed(
                camera_id=self.camera_id,
                junction_id=self.junction_id,
                fps=self.max_fps
            )
            self._status = "SIMULATED_ACTIVE"
            return True

        # Check if URL is a webcam index (e.g., "0", "1")
        capture_target: Any = self.url
        if isinstance(self.url, str) and self.url.isdigit():
            capture_target = int(self.url)

        try:
            self._capture = cv2.VideoCapture(capture_target)
            # Optimize buffer size to drop delayed frames on network streams
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not self._capture.isOpened():
                self._status = "CONNECTION_FAILED"
                logger.warning(f"Failed to open video capture for {self.camera_id} at {self.url}")
                return False

            self._status = "CONNECTED"
            logger.info(f"Successfully connected to camera stream: {self.camera_id}")
            return True
        except Exception as e:
            self._status = "ERROR"
            logger.error(f"Error initializing camera capture {self.camera_id}: {e}")
            return False

    def _cleanup_capture(self) -> None:
        if self._capture:
            try:
                self._capture.release()
            except Exception:
                pass
            self._capture = None
        if self._synthetic_feed:
            self._synthetic_feed.release()
            self._synthetic_feed = None

    def _capture_loop(self) -> None:
        frame_interval = 1.0 / max(1, self.max_fps)
        while self._running:
            opened = self._open_capture()
            if not opened:
                logger.warning(
                    f"Camera {self.camera_id} disconnected. Retrying in {self.reconnect_interval}s..."
                )
                self._status = "RECONNECTING"
                time.sleep(self.reconnect_interval)
                continue

            last_frame_time = time.time()
            consecutive_failures = 0

            while self._running:
                loop_start = time.time()

                if self._synthetic_feed:
                    ret, frame = self._synthetic_feed.read()
                elif self._capture:
                    ret, frame = self._capture.read()
                else:
                    ret, frame = False, None

                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures > 10:
                        logger.warning(f"Exceeded dropped frame limit on {self.camera_id}. Triggering reconnect.")
                        break
                    time.sleep(0.05)
                    continue

                consecutive_failures = 0

                # Store latest frame thread-safely
                with self._lock:
                    self._latest_raw_frame = frame
                    if self._latest_annotated_frame is None:
                        self._latest_annotated_frame = frame

                # Frame rate throttling
                elapsed = time.time() - loop_start
                sleep_time = max(0.0, frame_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            self._cleanup_capture()
            if self._running:
                time.sleep(self.reconnect_interval)


class StreamManager:
    """
    Registry and lifecycle coordinator for all junction camera streams.
    """

    def __init__(self, camera_configs: List[CameraConfig]):
        self.sources: Dict[str, CameraSource] = {}
        for cfg in camera_configs:
            self.sources[cfg.camera_id] = CameraSource(cfg)

    def start_all(self) -> None:
        logger.info(f"Starting {len(self.sources)} camera streams...")
        for source in self.sources.values():
            source.start()

    def stop_all(self) -> None:
        logger.info("Stopping all camera streams...")
        for source in self.sources.values():
            source.stop()

    def get_source(self, camera_id: str) -> Optional[CameraSource]:
        return self.sources.get(camera_id)

    def get_source_by_junction(self, junction_id: str) -> Optional[CameraSource]:
        for source in self.sources.values():
            if source.junction_id == junction_id:
                return source
        return None

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        statuses = {}
        for cam_id, src in self.sources.items():
            statuses[cam_id] = {
                "camera_id": cam_id,
                "junction_id": src.junction_id,
                "url": src.url,
                "status": src.status,
                "is_simulated": src.is_simulated
            }
        return statuses

    def generate_mjpeg_stream(self, camera_id: str) -> Generator[bytes, None, None]:
        """
        Yields multipart JPEG frames for live browser consumption.
        """
        source = self.get_source(camera_id)
        if not source:
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, f"CAMERA NOT FOUND: {camera_id}", (50, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            _, buf = cv2.imencode('.jpg', placeholder)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            return

        while True:
            frame = source.get_latest_frame(annotated=True)
            if frame is None:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, f"AWAITING FEED: {camera_id}", (100, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)

            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.04)  # ~25 FPS
