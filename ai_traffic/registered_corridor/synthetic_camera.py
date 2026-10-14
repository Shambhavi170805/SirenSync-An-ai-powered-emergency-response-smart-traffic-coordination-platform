"""Deterministic sample road camera containing a registered-looking ambulance plate."""

import time
from typing import Optional
import cv2
import numpy as np


class SyntheticRoadCamera:
    def __init__(self, camera_id: str, junction_id: str):
        self.camera_id = camera_id
        self.junction_id = junction_id
        self.plate: str | None = None
        self.vehicle_y = 500
        self.active = False
        self._last_dispatch = 0.0

    def dispatch(self, plate: str) -> None:
        self.plate = plate
        self.vehicle_y = 470
        self.active = True
        self._last_dispatch = time.time()

    def read(self) -> tuple[np.ndarray, Optional[str]]:
        frame = np.full((480, 800, 3), (49, 80, 54), dtype=np.uint8)
        cv2.rectangle(frame, (180, 0), (620, 480), (54, 56, 58), -1)
        for y in range(0, 480, 48):
            cv2.line(frame, (400, y), (400, y + 22), (235, 225, 190), 3)
        cv2.rectangle(frame, (0, 0), (800, 38), (18, 27, 42), -1)
        cv2.putText(frame, f"{self.camera_id}  ·  SAMPLE ROAD CAMERA", (18, 26), cv2.FONT_HERSHEY_SIMPLEX, .65, (200, 232, 255), 1)
        visible_plate = None
        if self.active and self.plate:
            self.vehicle_y -= 2
            y = self.vehicle_y
            cv2.rectangle(frame, (303, y - 70), (497, y + 60), (232, 238, 240), -1)
            cv2.rectangle(frame, (318, y - 54), (482, y - 8), (27, 45, 58), -1)
            cv2.rectangle(frame, (332, y + 17), (468, y + 42), (250, 250, 245), -1)
            cv2.rectangle(frame, (332, y + 17), (468, y + 42), (20, 26, 35), 2)
            cv2.putText(frame, self.plate, (337, y + 35), cv2.FONT_HERSHEY_SIMPLEX, .55, (10, 15, 20), 2)
            cv2.putText(frame, "AMBULANCE", (346, y - 72), cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 40, 215), 2)
            visible_plate = self.plate if 30 < y < 450 else None
            if y < -90:
                self.active = False
        return frame, visible_plate
