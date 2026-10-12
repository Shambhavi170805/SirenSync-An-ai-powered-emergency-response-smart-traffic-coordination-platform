"""
YOLOv10 Emergency Vehicle Detector.
Runs real-time inference on camera frames. Loads custom ambulance weights if available;
otherwise gracefully falls back to COCO vehicle detection + emergency strobe beacon heuristic
and logs the fallback state clearly.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple
import cv2
import numpy as np

from ai_traffic.core.config import DetectionConfig
from ai_traffic.core.logger import logger
from ai_traffic.detection.beacon_heuristic import BeaconColorHeuristic
from ai_traffic.detection.tracker import TemporalSmoothingTracker


@dataclass
class DetectionResult:
    has_ambulance: bool
    is_confirmed: bool
    just_confirmed: bool
    confidence: float
    bounding_box: Optional[List[int]]
    annotated_frame: np.ndarray
    heuristic_used: bool
    consecutive_frames: int
    details: Optional[dict] = None


class EmergencyVehicleDetector:
    """
    Inference coordinator for junction camera streams.
    """

    def __init__(self, config: DetectionConfig):
        self.config = config
        self.heuristic = BeaconColorHeuristic(config.heuristic)
        self.tracker = TemporalSmoothingTracker(config.temporal_smoothing_frames)

        self.model: Any = None
        self.is_custom_model = False
        self._load_model()

    def _load_model(self) -> None:
        custom_path = Path(self.config.custom_weights)

        try:
            from ultralytics import YOLO

            if custom_path.exists():
                logger.info(f"[DETECTION INFO] Loading custom fine-tuned ambulance weights from: {custom_path}")
                self.model = YOLO(str(custom_path))
                self.is_custom_model = True
            else:
                logger.warning(
                    f"[DETECTION FALLBACK] Custom ambulance weights not found at '{custom_path}'. "
                    f"Falling back to COCO vehicle detection (classes: car, bus, truck) "
                    f"combined with emergency beacon & strobe color heuristic."
                )
                base_model_name = self.config.base_model
                logger.info(f"Loading base YOLO model: {base_model_name}")
                self.model = YOLO(base_model_name)
                self.is_custom_model = False

        except Exception as e:
            logger.warning(
                f"[DETECTION WARNING] Could not initialize PyTorch/Ultralytics model ({e}). "
                "Operating in heuristic vision fallback mode (HSV strobe & emergency beacon scanner)."
            )
            self.model = None
            self.is_custom_model = False

    def detect(self, frame: np.ndarray, camera_id: str) -> DetectionResult:
        if frame is None or frame.size == 0:
            empty = np.zeros((480, 640, 3), dtype=np.uint8)
            return DetectionResult(
                has_ambulance=False,
                is_confirmed=False,
                just_confirmed=False,
                confidence=0.0,
                bounding_box=None,
                annotated_frame=empty,
                heuristic_used=False,
                consecutive_frames=0
            )

        annotated = frame.copy()
        raw_detection_found = False
        best_confidence = 0.0
        best_bbox: Optional[List[int]] = None
        heuristic_applied = False
        detection_details = {}

        if self.model is not None:
            # Real YOLO Inference
            try:
                results = self.model(
                    frame,
                    conf=self.config.confidence_threshold,
                    iou=self.config.iou_threshold,
                    imgsz=self.config.img_size,
                    verbose=False
                )
                boxes = results[0].boxes

                if self.is_custom_model:
                    # Model specifically trained on ambulance class (class id 0)
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        if cls_id == 0:  # Ambulance
                            raw_detection_found = True
                            if conf > best_confidence:
                                best_confidence = conf
                                best_bbox = xyxy
                else:
                    # Fallback COCO model: detect car (2), bus (5), truck (7) and run beacon heuristic
                    heuristic_applied = True
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        if cls_id in self.config.heuristic.vehicle_classes:
                            x1, y1, x2, y2 = xyxy
                            h, w = frame.shape[:2]
                            crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]

                            is_amb, h_conf, metrics = self.heuristic.analyze_vehicle(crop)
                            if is_amb:
                                raw_detection_found = True
                                combined_conf = round(0.4 * conf + 0.6 * h_conf, 2)
                                if combined_conf > best_confidence:
                                    best_confidence = combined_conf
                                    best_bbox = xyxy
                                    detection_details = metrics
                            else:
                                # Regular vehicle: draw faint bounding box
                                cv2.rectangle(annotated, (x1, y1), (x2, y2), (120, 120, 120), 1)
                                cv2.putText(annotated, f"Vehicle {conf:.2f}", (x1, max(15, y1 - 4)),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

            except Exception as ex:
                logger.debug(f"YOLO inference error on {camera_id}: {ex}")
                # Fallback to direct heuristic frame scan if model errors
                raw_detection_found, best_confidence, best_bbox, heuristic_applied = self._heuristic_frame_scan(frame)
        else:
            # Standalone heuristic frame scan when Ultralytics model unavailable
            raw_detection_found, best_confidence, best_bbox, heuristic_applied = self._heuristic_frame_scan(frame)

        # Update Temporal Smoothing Tracker
        is_confirmed, just_confirmed, consecutive_count = self.tracker.process_frame_detection(
            camera_id=camera_id,
            detected=raw_detection_found,
            bbox=best_bbox,
            confidence=best_confidence
        )

        # Annotate emergency vehicle on frame
        if best_bbox is not None:
            x1, y1, x2, y2 = best_bbox
            if is_confirmed:
                box_color = (0, 0, 255)  # Red alert bounding box
                status_text = f"AMBULANCE [CONFIRMED {int(best_confidence * 100)}%]"
                thickness = 3
            else:
                box_color = (0, 165, 255)  # Orange warning bounding box (pending smoothing)
                status_text = f"AMBULANCE [PENDING {consecutive_count}/{self.config.temporal_smoothing_frames}]"
                thickness = 2

            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, thickness)
            cv2.rectangle(annotated, (x1, max(0, y1 - 25)), (x1 + 320, max(25, y1)), box_color, -1)
            cv2.putText(annotated, status_text, (x1 + 6, max(18, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Add HUD overlay at top of annotated frame
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 28), (20, 20, 20), -1)
        model_type_str = "CUSTOM WEIGHTS" if self.is_custom_model else "COCO + BEACON HEURISTIC (FALLBACK)"
        cv2.putText(annotated, f"DETECTOR: {model_type_str}", (10, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 255), 1)

        tracker_hud = f"CONFIRMED: {is_confirmed} (STREAK: {consecutive_count})"
        hud_color = (0, 255, 100) if is_confirmed else (200, 200, 200)
        cv2.putText(annotated, tracker_hud, (annotated.shape[1] - 280, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, hud_color, 1)

        return DetectionResult(
            has_ambulance=raw_detection_found,
            is_confirmed=is_confirmed,
            just_confirmed=just_confirmed,
            confidence=best_confidence,
            bounding_box=best_bbox,
            annotated_frame=annotated,
            heuristic_used=heuristic_applied,
            consecutive_frames=consecutive_count,
            details=detection_details
        )

    def _heuristic_frame_scan(self, frame: np.ndarray) -> Tuple[bool, float, Optional[List[int]], bool]:
        """
        Scans frame for emergency strobe beacon signatures when deep learning model is not running.
        Identifies high-contrast flashing red and blue strobe clusters.
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Look for intense red & blue strobe lights
        red_mask = cv2.inRange(hsv, np.array([0, 140, 160]), np.array([10, 255, 255]))
        blue_mask = cv2.inRange(hsv, np.array([100, 140, 160]), np.array([130, 255, 255]))
        strobe_mask = cv2.bitwise_or(red_mask, blue_mask)

        # Find connected components / contours of strobe flashes
        contours, _ = cv2.findContours(strobe_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 15 < area < 1200:
                bx, by, bw, bh = cv2.boundingRect(cnt)
                # Expand box to simulate vehicle boundary around beacon
                vx1 = max(0, bx - 30)
                vy1 = max(0, by - 15)
                vx2 = min(w, bx + bw + 30)
                vy2 = min(h, by + bh + 65)

                crop = frame[vy1:vy2, vx1:vx2]
                is_amb, conf, _ = self.heuristic.analyze_vehicle(crop)
                if is_amb or area > 40:
                    return True, max(0.65, conf), [vx1, vy1, vx2, vy2], True

        return False, 0.0, None, True
