"""
Synthetic Traffic Video Generator.
Generates realistic simulated junction camera frames with traffic and periodic
or user-triggered emergency ambulances (including flashing red/blue strobe beacons).
Guarantees out-of-the-box demo execution without requiring physical cameras or RTSP streams.
"""

import math
import time
from typing import Optional, Tuple
import cv2
import numpy as np


class SyntheticTrafficFeed:
    """
    Renders an animated 640x480 traffic junction feed using OpenCV primitives.
    """

    def __init__(self, camera_id: str = "CAM-DEMO", junction_id: str = "J-101", fps: int = 25):
        self.camera_id = camera_id
        self.junction_id = junction_id
        self.fps = fps
        self.width = 640
        self.height = 480

        self.frame_count = 0
        self._ambulance_active = False
        self._ambulance_y = self.height + 60
        self._ambulance_speed = 7.0
        self._next_auto_ambulance_frame = 75  # Appear early for demo

        # Traffic vehicles: (x, y, speed, color, length, width)
        self.vehicles = [
            {"x": 220, "y": 100, "speed": 3.0, "color": (180, 180, 180), "h": 50, "w": 30},
            {"x": 220, "y": 300, "speed": 2.5, "color": (60, 60, 200), "h": 55, "w": 30},
            {"x": 380, "y": 400, "speed": -3.5, "color": (200, 120, 50), "h": 60, "w": 32},
            {"x": 380, "y": 150, "speed": -2.0, "color": (80, 180, 80), "h": 45, "w": 28},
        ]

    def trigger_ambulance(self) -> None:
        """Forces an ambulance to start its approach immediately."""
        self._ambulance_active = True
        self._ambulance_y = self.height + 60

    def read(self) -> Tuple[bool, np.ndarray]:
        """Generates the next frame."""
        self.frame_count += 1
        frame = np.full((self.height, self.width, 3), (45, 50, 45), dtype=np.uint8)  # Grass background

        # Draw intersection roads (dark asphalt)
        cv2.rectangle(frame, (180, 0), (460, self.height), (40, 40, 40), -1)  # Vertical road
        cv2.rectangle(frame, (0, 160), (self.width, 320), (40, 40, 40), -1)  # Horizontal road

        # Junction center box
        cv2.rectangle(frame, (180, 160), (460, 320), (35, 35, 35), -1)

        # Lane markings (dashed yellow / white)
        center_x = self.width // 2
        center_y = self.height // 2
        for y in range(0, self.height, 30):
            if not (150 < y < 330):
                cv2.line(frame, (center_x, y), (center_x, y + 15), (255, 255, 255), 2)
        for x in range(0, self.width, 30):
            if not (170 < x < 470):
                cv2.line(frame, (x, center_y), (x + 15, center_y), (0, 220, 240), 2)

        # Pedestrian Crosswalks
        for x in range(190, 450, 20):
            cv2.rectangle(frame, (x, 145), (x + 12, 155), (220, 220, 220), -1)
            cv2.rectangle(frame, (x, 325), (x + 12, 335), (220, 220, 220), -1)

        # Update and render regular civilian vehicles
        for v in self.vehicles:
            v["y"] += v["speed"]
            if v["speed"] > 0 and v["y"] > self.height + 60:
                v["y"] = -60
            elif v["speed"] < 0 and v["y"] < -60:
                v["y"] = self.height + 60

            # Render vehicle chassis
            vx, vy, vw, vh = int(v["x"]), int(v["y"]), v["w"], v["h"]
            cv2.rectangle(frame, (vx - vw // 2, vy - vh // 2), (vx + vw // 2, vy + vh // 2), v["color"], -1)
            # Windshields
            cv2.rectangle(frame, (vx - vw // 2 + 3, vy - 10), (vx + vw // 2 - 3, vy - 4), (20, 20, 20), -1)

        # Automatic periodic ambulance dispatch
        if not self._ambulance_active and self.frame_count >= self._next_auto_ambulance_frame:
            self.trigger_ambulance()
            self._next_auto_ambulance_frame = self.frame_count + 300  # repeat every ~12 seconds

        # Render ambulance if active
        if self._ambulance_active:
            self._ambulance_y -= self._ambulance_speed
            amb_x = 240  # Northbound lane
            amb_y = int(self._ambulance_y)
            amb_w = 42
            amb_h = 74

            # Main white body
            cv2.rectangle(frame, (amb_x - amb_w // 2, amb_y - amb_h // 2),
                          (amb_x + amb_w // 2, amb_y + amb_h // 2), (245, 245, 245), -1)

            # Red side stripes & cross
            cv2.line(frame, (amb_x - amb_w // 2, amb_y), (amb_x + amb_w // 2, amb_y), (0, 0, 230), 4)
            # Cross on roof
            cv2.line(frame, (amb_x - 7, amb_y - 12), (amb_x + 7, amb_y - 12), (0, 0, 230), 3)
            cv2.line(frame, (amb_x, amb_y - 19), (amb_x, amb_y - 5), (0, 0, 230), 3)

            # Windshield (dark glass)
            cv2.rectangle(frame, (amb_x - amb_w // 2 + 4, amb_y - 30),
                          (amb_x + amb_w // 2 - 4, amb_y - 20), (30, 30, 30), -1)

            # Strobe Beacon (flashing red and blue alternately)
            beacon_phase = (self.frame_count // 3) % 2
            left_color = (0, 0, 255) if beacon_phase == 0 else (255, 100, 0)   # Red / Blue
            right_color = (255, 100, 0) if beacon_phase == 0 else (0, 0, 255)

            # Left and right roof beacons
            cv2.circle(frame, (amb_x - 12, amb_y - 25), 6, left_color, -1)
            cv2.circle(frame, (amb_x + 12, amb_y - 25), 6, right_color, -1)

            # Light bloom / glow effect around active strobes
            cv2.circle(frame, (amb_x - 12, amb_y - 25), 14, left_color, 1)
            cv2.circle(frame, (amb_x + 12, amb_y - 25), 14, right_color, 1)

            # Check if ambulance crossed and left scene
            if self._ambulance_y < -80:
                self._ambulance_active = False

        # Add Telemetry & Feed Metadata Banner
        cv2.rectangle(frame, (0, 0), (self.width, 36), (15, 15, 15), -1)
        cv2.putText(frame, f"FEED: {self.camera_id} [{self.junction_id}]", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 1, cv2.LINE_AA)

        sim_tag = "SIMULATED / TEST FEED"
        cv2.putText(frame, sim_tag, (self.width - 205, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 215, 255), 1, cv2.LINE_AA)

        # Timestamp overlay
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, ts_str, (10, self.height - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

        return True, frame

    def release(self) -> None:
        pass
